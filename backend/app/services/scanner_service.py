import asyncio
import logging
import mimetypes
import os
import time
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.websocket import manager
from app.core.database import get_db
from app.core.exceptions import FunctionalError, TechnicalError
from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.enums import ConnectorStatus, DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion.utils import IngestionUtils
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)


class ScannerService:
    """
    Service responsible for scanning file systems and syncing document records in the database.
    Handles non-blocking I/O for file system operations and manages batch updates to the database.
    """

    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".csv",
        ".json",
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".aac",
        ".ogg",
        ".zip",
        ".eml",
        ".msg",
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".bmp",
        ".heic",
    }

    IGNORED_PREFIXES = (".", "~")
    IGNORED_FILES = {"Thumbs.db", "desktop.ini", ".DS_Store"}

    def __init__(
        self,
        db: AsyncSession,
        connector_repo: Optional[ConnectorRepository] = None,
        document_repo: Optional[DocumentRepository] = None,
        vector_service: Optional[VectorService] = None,
    ):
        self.db = db
        self.connector_repo = connector_repo or ConnectorRepository(db)
        self.document_repo = document_repo or DocumentRepository(db)
        self.vector_service = vector_service

    async def _run_blocking_io(self, func, *args, **kwargs):
        """Wrapper to offload blocking I/O to thread pool."""
        return await asyncio.to_thread(func, *args, **kwargs)

    async def scan_folder(self, connector_id: UUID, base_path: str, recursive: bool = True) -> Dict[str, int]:
        """
        Scans a folder and syncs ConnectorDocument records with the actual file system state.
        Detects additions, updates, and deletions.
        """
        start_time = time.time()
        logger.info(f"START | ScannerService.scan_folder | connector={connector_id}, path={base_path}")

        # P0 Fix: Non-blocking existence check
        if not await self._run_blocking_io(os.path.exists, base_path):
            raise TechnicalError(message=f"Path not found: {base_path}", error_code="PATH_NOT_FOUND")

        try:
            # 1. Fetch context
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise TechnicalError(message=f"Connector {connector_id} not found", error_code="CONNECTOR_NOT_FOUND")

            # P0: Always set to IDLE during scan to prevent auto-ingestion
            # The user must manually click 'Process' or wait for the scheduled sync
            initial_status = DocStatus.IDLE

            await self._safe_emit("SCAN_STARTED", {"connector_id": str(connector_id), "message": "Scanning files..."})

            # 2. Fetch existing documents (TODO: Impl pagination for massive folders P1)
            # Using repo instead of direct select for consistency
            existing_docs_list = await self.document_repo.get_by_connector(connector_id, limit=20000)
            existing_docs = {doc.file_path: doc for doc in existing_docs_list}

            # 3. Walk directory
            found_files = await self._run_blocking_io(self._walk_directory_sync, base_path, recursive)
            logger.info(f"SCAN | Found {len(found_files)} candidates in {base_path}")

            stats = {"added": 0, "updated": 0, "ignored": 0, "deleted": 0}
            last_ws_update = time.time()

            # 4. Process found files
            to_create = []
            to_update = []
            to_delete_ids = []

            stats = {"added": 0, "updated": 0, "ignored": 0, "deleted": 0}
            last_ws_update = time.time()

            for idx, (rel_path, full_path) in enumerate(found_files.items(), 1):
                # Throttle WebSocket updates
                if idx % 100 == 0 or (time.time() - last_ws_update) > 1.0:
                    await self._safe_emit(
                        "SCANNING_PROGRESS",
                        {
                            "connector_id": str(connector_id),
                            "current_file": rel_path,
                            "progress": f"{idx}/{len(found_files)}",
                        },
                    )
                    last_ws_update = time.time()

                action, data = await self._determine_file_delta(
                    rel_path,
                    full_path,
                    existing_docs.get(rel_path),
                    connector_id,
                    initial_status,
                    connector.connector_type,
                )

                if action == "create":
                    to_create.append(data)
                elif action == "update":
                    to_update.append(data)
                elif action == "ignore":
                    to_create.append(data)  # "Ignore" means create as UNSUPPORTED
                elif action == "update_ignore":
                    to_update.append(data)

                # Periodically flush to prevent massive memory usage if 100k+ files
                if len(to_create) >= 500:
                    await self.document_repo.create_batch(to_create)
                    stats["added"] += len([d for d in to_create if d.get("status") != DocStatus.UNSUPPORTED])
                    stats["ignored"] += len([d for d in to_create if d.get("status") == DocStatus.UNSUPPORTED])
                    to_create = []
                if len(to_update) >= 500:
                    updated_batch_count = await self.document_repo.update_batch(to_update)
                    # We can't easily distinguish which were ignored vs updated without more logic,
                    # but for stats, "updated" usually implies a change in a supported file.
                    # For simplicity, we count all successful updates as 'updated'.
                    stats["updated"] += updated_batch_count
                    to_update = []

            # 5. Handle deletions
            for rel_path, doc in existing_docs.items():
                if rel_path not in found_files:
                    to_delete_ids.append(doc.id)

            # Final flushes
            if to_create:
                await self.document_repo.create_batch(to_create)
                stats["added"] += len([d for d in to_create if d.get("status") != DocStatus.UNSUPPORTED])
                stats["ignored"] += len([d for d in to_create if d.get("status") == DocStatus.UNSUPPORTED])
            if to_update:
                updated_count = await self.document_repo.update_batch(to_update)
                stats["updated"] += updated_count  # This is a bit rough on the stats but accurate enough
            if to_delete_ids:
                deleted_count = await self.document_repo.delete_batch(to_delete_ids)
                stats["deleted"] = deleted_count

            # 6. Commit and Cleanup
            await self.db.commit()

            # POST-COMMIT: Trigger vector cleanup only if DB commit succeeded (Atomicity)
            if to_delete_ids:
                for d_id in to_delete_ids:
                    logger.info(f"Removing vectors for zombie file ID: {d_id}")
                    # P1 FIX: Use VectorService directly to avoid IngestionService circular dep
                    asyncio.create_task(self._safe_delete_vectors(d_id))
                    await manager.emit_document_deleted(str(d_id), str(connector_id))

            # 7. Update connector stats
            total_count = await self.document_repo.count_by_connector(connector_id)
            updated_connector = await self.connector_repo.update(connector_id, {"total_docs_count": total_count})

            # P0 Fix: Emit update so frontend sees file count immediately
            from app.schemas.connector import ConnectorResponse

            resp = ConnectorResponse.model_validate(updated_connector)
            await manager.emit_connector_updated(resp.model_dump(mode="json"))

            logger.info(
                f"FINISH | scan_folder | Duration: {round((time.time() - start_time) * 1000, 2)}ms | Stats: {stats}"
            )
            await self._safe_emit("SCAN_COMPLETE", {"connector_id": str(connector_id), "stats": stats})

            return stats

        except Exception as e:
            logger.error(f"❌ FAIL | scan_folder | Error: {e}", exc_info=True)
            await self.db.rollback()
            raise TechnicalError(f"Scan failed: {e}", error_code="SCAN_FOLDER_ERROR")

    async def _determine_file_delta(
        self,
        rel_path: str,
        full_path: str,
        doc: Optional[ConnectorDocument],
        connector_id: UUID,
        initial_status: DocStatus,
        connector_type: str,
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Determines what change is needed for a file without executing it."""
        ext = os.path.splitext(full_path)[1].lower()
        is_supported = ext in self.SUPPORTED_EXTENSIONS
        validation_error: Optional[str] = None

        # Logic to exclude CSVs from local_folder
        if connector_type == "local_folder" and ext == ".csv":
            is_supported = False
            validation_error = "CSV files are not supported in Folder connectors. Use the CSV File connector instead."

        # Logic to exclude non-CSVs from local_file
        if connector_type == "local_file" and ext != ".csv":
            is_supported = False
            validation_error = "Only CSV files are supported in this connector type."

        if is_supported and ext == ".csv":
            try:
                await IngestionUtils.validate_csv_file(full_path)
            except (FunctionalError, ValueError) as e:
                is_supported = False
                validation_error = str(e)
            except Exception as e:
                is_supported = False
                validation_error = f"Validation Error: {str(e)}"

        try:
            file_stat = await self._run_blocking_io(os.stat, full_path)
            file_size = file_stat.st_size
            last_modified = datetime.fromtimestamp(file_stat.st_mtime)
        except OSError:
            return None, None

        # Eliminated slow hashing: We rely on file_size + mtime + LlamaIndex component caching

        if not doc:
            if is_supported:
                return "create", {
                    "connector_id": connector_id,
                    "file_path": rel_path,
                    "file_name": os.path.basename(full_path),
                    "file_size": file_size,
                    "last_modified_at_source": last_modified,
                    "status": initial_status,
                    "mime_type": self._detect_mime_type(full_path),
                    "file_metadata": {
                        "file_name": os.path.basename(full_path),
                        "file_path": rel_path,
                        "file_size": file_size,
                        "file_type": self._detect_mime_type(full_path),
                        "creation_date": datetime.fromtimestamp(file_stat.st_ctime).strftime("%Y-%m-%d"),
                        "last_modified_date": last_modified.strftime("%Y-%m-%d"),
                    },
                }
            else:
                reason = validation_error or "Unsupported extension"
                return "ignore", {
                    "connector_id": connector_id,
                    "file_path": rel_path,
                    "file_name": os.path.basename(full_path),
                    "status": DocStatus.UNSUPPORTED,
                    "file_metadata": {
                        "file_name": os.path.basename(full_path),
                        "file_path": rel_path,
                        "file_type": IngestionUtils.detect_mime_type(full_path),
                        "reason": reason,
                    },
                }
        else:
            # UPDATE Logic
            if not is_supported:
                if doc.status != DocStatus.UNSUPPORTED:
                    reason = validation_error or "Unsupported extension"
                    return "update_ignore", {
                        "id": doc.id,
                        "status": DocStatus.UNSUPPORTED,
                        "file_metadata": {**dict(doc.file_metadata or {}), "reason": reason},
                    }
            else:
                # Optimized Change Detection: Size + MTime
                # If either changed, we re-ingest.
                # Note: last_modified_at_source in DB might be timezone aware, ensure comparison works
                # Usually both are naive or both aware in usage, but let's be careful.
                # Ideally, we assume strict inequality triggers update.
                size_changed = doc.file_size != file_size

                # Careful with float comparison/tz, but != usually works for timestamps from same OS
                time_changed = doc.last_modified_at_source != last_modified

                if size_changed or time_changed or doc.status == DocStatus.FAILED:
                    return "update", {
                        "id": doc.id,
                        "file_size": file_size,
                        "last_modified_at_source": last_modified,
                        "status": initial_status,
                    }
        return None, None

    def _walk_directory_sync(self, base_path: str, recursive: bool) -> Dict[str, str]:
        """Synchronous directory walk (or single file check)."""
        found_files = {}

        # Handle single file case
        if os.path.isfile(base_path):
            base_name = os.path.basename(base_path)
            if not (base_name.startswith(self.IGNORED_PREFIXES) or base_name in self.IGNORED_FILES):
                # For single file, use the full path as rel_path to preserve directory structure
                found_files[base_path] = base_path
            return found_files

        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if not (d.startswith(self.IGNORED_PREFIXES) or d in self.IGNORED_FILES)]
            for file in files:
                if file.startswith(self.IGNORED_PREFIXES) or file in self.IGNORED_FILES:
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_path)
                if not recursive and os.path.abspath(root) != os.path.abspath(base_path):
                    continue
                found_files[rel_path] = full_path
        return found_files

    async def _safe_delete_vectors(self, doc_id: UUID):
        """Standardized background vector cleanup."""
        try:
            if self.vector_service:
                await self.vector_service.delete_document_vectors(str(doc_id))
            else:
                logger.warning(f"VectorService not available for cleaning up document {doc_id}")
        except Exception as e:
            logger.warning(f"Background vector cleanup failed for {doc_id}: {e}")

    async def _safe_emit(self, event: str, data: dict):
        """Safe WebSocket emit."""
        try:
            await manager.emit_dashboard_update(event, data)
        except Exception as e:
            logger.debug(f"WS emit failed for {event}: {e}")

    def _detect_mime_type(self, full_path: str) -> str:
        """Helper to detect mime type via IngestionUtils."""
        return IngestionUtils.detect_mime_type(full_path)


async def get_scanner_service(
    db: Annotated[AsyncSession, Depends(get_db)], vector_service: Annotated[VectorService, Depends(get_vector_service)]
) -> ScannerService:
    """Dependency provider for ScannerService."""
    return ScannerService(db, vector_service=vector_service)
