import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager, Websocket, get_websocket
from app.core.database import SessionLocal, get_db
from app.core.exceptions import EntityNotFound, FunctionalError, InternalDataCorruption, TechnicalError
from app.models.connector import Connector
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.connector import ConnectorCreate, ConnectorResponse, ConnectorUpdate
from app.schemas.enums import ConnectorStatus, ConnectorType
from app.services.ingestion_service import IngestionService
from app.services.scanner_service import ScannerService
from app.services.settings_service import SettingsService, get_settings_service
from app.services.sql_discovery_service import SQLDiscoveryService, get_sql_discovery_service
from app.services.vector_service import VectorService, get_vector_service
from app.repositories.connector_sync_log_repository import ConnectorSyncLogRepository
from app.core.interfaces.base_connector import translate_host_path

logger = logging.getLogger(__name__)

# 🔵 P3: Extracted Magic Literals & Config
SCHEDULE_MAP = {
    "daily": "0 0 * * *",
    "weekly": "0 0 * * 0",
    "monthly": "0 0 1 * *",
    "5m": "*/5 * * * *",
    "manual": None,
}

# 🔴 P0: Security Constraint - Only allow deletion in managed directories
MANAGED_UPLOAD_DIR = "temp_uploads"


class ConnectorService:
    """
    Architect Refactor of ConnectorService.
    Ensures Pydantic returns (P0), non-blocking IO (P0), and modular DI (P1).
    Security Hardened: Prevents arbitrary file deletion.
    """

    def __init__(
        self,
        connector_repo: ConnectorRepository,
        scanner_service: ScannerService,
        vector_service: Optional[VectorService] = None,
        settings_service: Optional[SettingsService] = None,
        sql_discovery_service: Optional[SQLDiscoveryService] = None,
    ):
        self.connector_repo = connector_repo
        self.sync_log_repo = ConnectorSyncLogRepository(connector_repo.db)  # Use same session
        self.scanner_service = scanner_service
        self.db = connector_repo.db
        self.settings_service = settings_service or SettingsService(self.db)
        self.vector_service = vector_service or VectorService(self.settings_service)
        self.sql_discovery_service = sql_discovery_service or SQLDiscoveryService(self.db, self.settings_service)

        # 🟠 P1: Prevent GC of fire-and-forget tasks (Instance-level)
        self._background_tasks: Set[asyncio.Task] = set()

    @staticmethod
    async def _run_blocking_io(func, *args):
        """Wrapper for safe non-blocking IO operations. Fixes P0 Blocking IO."""
        return await asyncio.to_thread(func, *args)

    def _track_task(self, coro) -> asyncio.Task:
        """
        🟠 P1: Robust Background Task Execution.
        Creates a task and keeps a strong reference to prevent GC during execution.
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def get_connectors(self) -> List[ConnectorResponse]:
        """
        Retrieves all connectors with computed last_vectorized_at.
        Fixes P0: Returns ConnectorResponse.
        """
        start_time = time.time()
        func_name = "ConnectorService.get_connectors"

        try:
            # 🟠 P1: Potential N+1 / Large Payload.
            # Ideally should accept pagination params (skip, limit).
            # Assuming Repo handles efficient fetching.
            connectors = await self.connector_repo.get_all_with_stats()

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"FETCH | {func_name} | Count: {len(connectors)} | {elapsed}ms")

            # 🔴 P0: Convert ORM to Pydantic
            return [ConnectorResponse.model_validate(c) for c in connectors]

        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | {e}", exc_info=True)
            raise TechnicalError(f"Failed to fetch connectors: {e}", error_code="FETCH_ERROR")

    async def get_connector(self, connector_id: UUID) -> Optional[ConnectorResponse]:
        """
        Fetch single connector.
        Fixes P0: Returns ConnectorResponse.
        """
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                return None
            return ConnectorResponse.model_validate(connector)
        except Exception as e:
            logger.error(f"❌ FAIL | Connector retrieval {connector_id} | {e}")
            raise TechnicalError(f"Fetch failed", error_code="FETCH_ERROR")

    async def create_connector(self, connector_data: ConnectorCreate) -> ConnectorResponse:
        """
        Create new connector and trigger initial background scan.
        Fixes P0: Returns ConnectorResponse.
        """
        start_time = time.time()
        func_name = "ConnectorService.create_connector"

        try:
            # 1. Validation Logic
            # ARCHITECT FIX: Prioritize explicit cron from frontend
            if connector_data.schedule_cron:
                schedule_cron = connector_data.schedule_cron
            else:
                schedule_cron = self._resolve_schedule(connector_data.schedule_type)

            # 🟡 P2: Use Enum instead of Magic String
            if connector_data.connector_type == ConnectorType.LOCAL_FILE:
                await self._validate_file_path(connector_data.configuration, connector_data.connector_type)
            elif connector_data.connector_type == ConnectorType.LOCAL_FOLDER:
                await self._validate_folder_path(connector_data.configuration)

            # 2. DB Creation
            data = connector_data.model_dump()
            data["schedule_cron"] = schedule_cron
            data["status"] = ConnectorStatus.IDLE

            new_connector = await self.connector_repo.create(data)

            # 3. Side Effects (Backgrounded)
            if new_connector.connector_type in [ConnectorType.LOCAL_FILE, ConnectorType.LOCAL_FOLDER]:
                # 🟠 P1: Supervised background task
                self._track_task(self._safe_background_scan(new_connector.id, new_connector.configuration))
            elif new_connector.connector_type == ConnectorType.SQL:
                # 🔵 Automatic Discovery for SQL
                self._track_task(self.scan_connector(new_connector.id))

            resp = ConnectorResponse.model_validate(new_connector)
            await manager.emit_connector_created(resp.model_dump(mode="json"))

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"CREATED | {func_name} | {new_connector.id} | {elapsed}ms")

            return resp

        except (FunctionalError, IntegrityError):
            raise
        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | {e}", exc_info=True)
            raise TechnicalError("Creation failed", error_code="CREATION_ERROR") from e

    async def update_connector(self, connector_id: UUID, connector_update: ConnectorUpdate) -> ConnectorResponse:
        """
        Partial update of connector with configuration change handling.
        Fixes P0: Returns ConnectorResponse.
        """
        try:
            db_connector = await self.connector_repo.get_by_id(connector_id)
            if not db_connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            old_config = db_connector.configuration or {}
            update_data = connector_update.model_dump(exclude_unset=True)

            # ARCHITECT FIX: Prioritize explicit cron from frontend
            if connector_update.schedule_cron is not None:
                update_data["schedule_cron"] = connector_update.schedule_cron
            elif connector_update.schedule_type:
                # Only resolve if no explicit cron provided (Backward compat)
                resolved = self._resolve_schedule(connector_update.schedule_type)
                # FIX: Apply resolved schedule if type is known (even if resolved is None, e.g. manual)
                if connector_update.schedule_type in SCHEDULE_MAP:
                    update_data["schedule_cron"] = resolved

            if connector_update.configuration:
                # Type-specific validation
                if db_connector.connector_type == ConnectorType.LOCAL_FILE:
                    await self._validate_file_path(connector_update.configuration, db_connector.connector_type)
                elif db_connector.connector_type == ConnectorType.LOCAL_FOLDER:
                    await self._validate_folder_path(connector_update.configuration)

                    new_path = connector_update.configuration.get("path")
                    old_path = old_config.get("path")

                    new_recursive = connector_update.configuration.get("recursive")
                    old_recursive = old_config.get("recursive")

                    # ARCHITECT FIX: Automatic Stop on Critical Change
                    critical_change = (old_path and new_path != old_path) or (
                        new_recursive is not None and new_recursive != old_recursive
                    )

                    if critical_change:
                        if db_connector.status in [
                            ConnectorStatus.STARTING,
                            ConnectorStatus.SYNCING,
                            ConnectorStatus.VECTORIZING,
                        ]:
                            logger.info(f"🛑 Auto-Stopping connector {connector_id} due to config change.")
                            update_data["status"] = ConnectorStatus.IDLE

                    # 🔴 P0 SECURITY FIX: Only delete file if it was a MANAGED FILE and path changed.
                    # NEVER delete local folders or arbitrary user paths.
                    # For FOLDERS, we generally don't delete content on update, just path change.

                # Handle file deletion for LOCAL_FILE if path changed
                if db_connector.connector_type == ConnectorType.LOCAL_FILE and connector_update.configuration:
                    new_path = connector_update.configuration.get("path")
                    old_path = old_config.get("path")

                    if old_path and new_path != old_path:
                        # Only delete if it appears to be in our managed upload dir (Security Guard)
                        if self._is_managed_path(old_path):
                            self._track_task(self._safe_delete_file(old_path))
                        else:
                            logger.warning(f"SKIPPING DELETION | path '{old_path}' is outside managed area.")

                # Update ACLs if changed (P1 backgrounded)
                new_acl = connector_update.configuration.get("connector_acl")
                if new_acl:
                    self._track_task(self._safe_update_acl(connector_id, new_acl, connector_update.configuration))

            # Apply via Repository
            updated_connector = await self.connector_repo.update(connector_id, update_data)

            # Invalidate SQL engine cache when connector configuration changes
            if self.sql_discovery_service and self.sql_discovery_service.engine_cache:
                if connector_update.configuration:
                    invalidated = self.sql_discovery_service.engine_cache.invalidate_connector(connector_id)
                    if invalidated > 0:
                        logger.info(
                            f"SQL_ENGINE_CACHE | Invalidated {invalidated} cached engines due to connector update"
                        )

            # Post-Update Side Effects
            if (
                updated_connector.connector_type in [ConnectorType.LOCAL_FILE, ConnectorType.LOCAL_FOLDER]
                and connector_update.configuration
            ):
                if updated_connector.status == ConnectorStatus.IDLE:
                    self._track_task(self._safe_background_scan(updated_connector.id, updated_connector.configuration))
            elif updated_connector.connector_type == ConnectorType.SQL and connector_update.configuration:
                # Trigger re-discovery on SQL config change
                self._track_task(self.scan_connector(updated_connector.id))

            resp = ConnectorResponse.model_validate(updated_connector)
            await manager.emit_connector_updated(resp.model_dump(mode="json"))
            return resp

        except Exception as e:
            if isinstance(e, (EntityNotFound, FunctionalError)):
                raise
            logger.error(f"❌ UPDATE FAIL | {connector_id} | {e}", exc_info=True)
            raise TechnicalError("Update failed", error_code="UPDATE_ERROR")

    async def delete_connector(self, connector_id: UUID) -> bool:
        """
        Delete connector and clean up external resources.
        Fixes P0: Uses non-blocking cleanup.
        """
        try:
            db_connector = await self.connector_repo.get_by_id(connector_id)
            if not db_connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            # 1. Async Cleanup External Resources
            if db_connector.configuration:
                # 🔴 P0 SECURITY FIX: Guarded Deletion
                if db_connector.connector_type == ConnectorType.LOCAL_FILE:
                    path = translate_host_path(db_connector.configuration.get("path"))
                    if path and self._is_managed_path(path):
                        self._track_task(self._safe_delete_file(path))

                # Vector DB cleanup
                self._track_task(self._safe_delete_vectors(connector_id, db_connector.configuration))

            # 2. DB Cleanup
            await self.connector_repo.delete_with_relations(connector_id)

            # Invalidate SQL engine cache when connector is deleted
            if self.sql_discovery_service and self.sql_discovery_service.engine_cache:
                invalidated = self.sql_discovery_service.engine_cache.invalidate_connector(connector_id)
                if invalidated > 0:
                    logger.info(
                        f"SQL_ENGINE_CACHE | Invalidated {invalidated} cached engines due to connector deletion"
                    )

            await manager.emit_connector_deleted(connector_id)
            return True

        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"❌ DELETE FAIL | {connector_id} | {e}", exc_info=True)
            raise TechnicalError("Delete failed", error_code="DELETE_ERROR")

    async def stop_connector(self, connector_id: UUID) -> ConnectorResponse:
        """Gracefully stop a running connector."""
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            if connector.status in [ConnectorStatus.STARTING, ConnectorStatus.SYNCING, ConnectorStatus.VECTORIZING]:
                updated = await self.connector_repo.update(connector_id, {"status": ConnectorStatus.PAUSED})
                resp = ConnectorResponse.model_validate(updated)
                await manager.emit_connector_updated(resp.model_dump(mode="json"))
                return resp

            return ConnectorResponse.model_validate(connector)
        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"Stop connector failed: {e}")
            raise TechnicalError("Failed to stop connector", error_code="STOP_ERROR")

    async def trigger_sync(self, connector_id: UUID, force: bool = False) -> ConnectorResponse:
        """Queue a connector for synchronization."""
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            if connector.status == ConnectorStatus.VECTORIZING:
                return ConnectorResponse.model_validate(connector)

            update_data = {"status": ConnectorStatus.QUEUED, "last_error": None}

            if force:
                new_conf = dict(connector.configuration or {})
                new_conf["force_sync"] = True
                update_data["configuration"] = new_conf

            updated = await self.connector_repo.update(connector_id, update_data)
            resp = ConnectorResponse.model_validate(updated)
            await manager.emit_connector_updated(resp.model_dump(mode="json"))
            return resp
        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"Trigger sync failed: {e}")
            raise TechnicalError("Trigger sync failed", error_code="SYNC_ERROR")

    async def scan_connector(self, connector_id: UUID) -> ConnectorResponse:
        """Triggers a MANUAL foreground scan."""
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            # 🟡 P2: Enum Usage
            # Supported types for manual scan
            supported_types = [
                ConnectorType.LOCAL_FILE,
                ConnectorType.LOCAL_FOLDER,
                ConnectorType.SQL,
                ConnectorType.VANNA_SQL,
            ]

            logger.info(
                f"SCAN START | Connector: {connector.id} | Type: {connector.connector_type} (Expected SQL: {ConnectorType.SQL})"
            )

            if connector.connector_type not in supported_types:
                raise FunctionalError(
                    f"Connector type '{connector.connector_type}' cannot be scanned manually", error_code="INVALID_TYPE"
                )

            # Branching Logic
            sync_log = await self.sync_log_repo.create_log(connector.id)
            stats = {"added": 0, "updated": 0, "deleted": 0}

            try:
                if connector.connector_type in [ConnectorType.SQL, ConnectorType.VANNA_SQL]:
                    # SQL Scan (including Vanna SQL)
                    logger.info("SCAN ROUTE | SQL PATH SELECTED")
                    stats = await self.sql_discovery_service.scan_and_persist_views(connector.id)

                elif connector.connector_type == ConnectorType.LOCAL_FILE:
                    # File Scan
                    logger.info("SCAN ROUTE | FILE PATH SELECTED")
                    path = translate_host_path(connector.configuration.get("path"))
                    if not path:
                        raise FunctionalError("Invalid config: path missing", error_code="INVALID_CONFIG")
                    stats = await self.scanner_service.scan_folder(connector.id, path, recursive=False)

                elif connector.connector_type == ConnectorType.LOCAL_FOLDER:
                    # Folder Scan
                    logger.info("SCAN ROUTE | FOLDER PATH SELECTED")
                    path = translate_host_path(connector.configuration.get("path"))
                    if not path:
                        raise FunctionalError("Invalid config: path missing", error_code="INVALID_CONFIG")
                    recursive = connector.configuration.get("recursive", False)
                    stats = await self.scanner_service.scan_folder(connector.id, path, recursive=recursive)

                else:
                    raise FunctionalError("Invalid config: unknown connector type", error_code="INVALID_CONFIG")

                # Log Success
                total_docs = stats.get("added", 0) + stats.get("updated", 0)
                await self.sync_log_repo.update_log(sync_log.id, status="success", documents_synced=total_docs)

            except Exception as e:
                # Log Failure
                await self.sync_log_repo.update_log(sync_log.id, status="failure", error_message=str(e))
                raise

            # Fetch fresh record after scan side-effects
            fresh = await self.connector_repo.get_by_id(connector_id)
            return ConnectorResponse.model_validate(fresh)

        except Exception as e:
            if isinstance(e, (EntityNotFound, FunctionalError, TechnicalError)):
                raise
            logger.error(f"Manual scan failed: {e}", exc_info=True)
            raise TechnicalError(f"Scan failed: {e}", error_code="SCAN_ERROR")

    async def train_vanna(
        self,
        connector_id: UUID,
        document_ids: List[UUID],
        document_service: Any,
    ) -> Dict[str, Any]:
        """
        Train Vanna AI on specific documents for vanna_sql connector.
        Refactored from API endpoint (P1).
        """
        connector = await self.get_connector(connector_id)
        if not connector:
            return {"success": False, "message": "Connector not found"}

        if connector.connector_type != ConnectorType.VANNA_SQL:
            return {"success": False, "message": "Training is only available for vanna_sql connectors"}

        # Use centralized Factory to get the correctly configured Vanna Service
        from app.services.chat.vanna_services import VannaServiceFactory

        vanna_svc = await VannaServiceFactory(
            self.settings_service,
            connector_id=connector_id,
            context_provider=connector.configuration.get("ai_provider"),
            connector_config=connector.configuration,
        )

        trained_count = 0
        failed_count = 0

        for doc_id in document_ids:
            try:
                document = await document_service.document_repo.get_by_id(doc_id)
                if not document:
                    logger.warning(f"Document {doc_id} not found, skipping")
                    failed_count += 1
                    continue

                ddl_content = (document.file_metadata or {}).get("ddl")
                if not ddl_content:
                    logger.warning(f"Document {doc_id} has no DDL content, skipping")
                    failed_count += 1
                    continue

                # Train Vanna - blocking call moved to thread
                await asyncio.to_thread(vanna_svc.train, ddl=ddl_content)

                # Mark as trained
                meta = document.file_metadata or {}
                meta["trained"] = True
                meta["trained_at"] = datetime.now(timezone.utc).isoformat()

                await document_service.update_document(document.id, {"file_metadata": meta})
                trained_count += 1
                logger.info(f"Trained Vanna on document: {document.file_name}")

            except Exception as doc_error:
                logger.error(f"Failed to train document {doc_id}: {doc_error}")
                failed_count += 1

        return {
            "success": True,
            "message": f"Training completed. {trained_count} documents trained, {failed_count} failed.",
            "trained_count": trained_count,
            "failed_count": failed_count,
        }

    # --- Helpers ---
    @staticmethod
    def _resolve_schedule(schedule_type: str) -> Optional[str]:
        """Maps simplified schedule types to cron expressions."""
        return SCHEDULE_MAP.get(schedule_type, None)

    @staticmethod
    def _is_managed_path(path: str) -> bool:
        """
        🔴 P0 SECURITY: Guardrail.
        Returns True if the path lies within the managed 'uploads' directory.
        Used to prevent accidental deletion of user system files.
        """
        if not path:
            return False
        try:
            # Normalize path
            abs_path = os.path.abspath(path)
            # We assume the uploads dir is relative to current working dir or configured root.
            # Ideally this should come from SettingsService, but strict relative check is a good start.
            managed_root = os.path.abspath(MANAGED_UPLOAD_DIR)
            return abs_path.startswith(managed_root)
        except Exception:
            return False

    @classmethod
    async def _validate_file_path(cls, config: dict, connector_type: ConnectorType):
        """Non-blocking validation of file existence and type."""
        if not config or "path" not in config:
            raise FunctionalError("Invalid config: path missing", error_code="INVALID_CONFIG", status_code=400)

        path = translate_host_path(config["path"])
        exists = await cls._run_blocking_io(os.path.isfile, path)
        if not exists:
            error_msg = f"File not found: {path}"
            from app.core.utils.storage import get_storage_status

            if not get_storage_status():
                error_msg += ". Note: Virtual/Network drives (G:, OneDrive) are not accessible via Docker."
            raise FunctionalError(error_msg, error_code="FILE_NOT_FOUND", status_code=400)

        # ARCHITECT FIX: Validate extension for CSV connectors
        if connector_type == ConnectorType.LOCAL_FILE:
            if not path.lower().endswith(".csv"):
                raise FunctionalError("This connector only supports CSV files", error_code="INVALID_EXTENSION")

    @classmethod
    async def _validate_folder_path(cls, config: dict):
        """Non-blocking validation of directory existence."""
        if not config or "path" not in config:
            return
        path = translate_host_path(config["path"])
        exists = await cls._run_blocking_io(os.path.isdir, path)
        if not exists:
            error_msg = f"Path not found: {path}"
            from app.core.utils.storage import get_storage_status

            if not get_storage_status():
                error_msg += ". Note: Virtual/Network drives (G:, OneDrive) are not accessible via Docker."
            raise FunctionalError(error_msg, error_code="PATH_NOT_FOUND", status_code=400)

    @classmethod
    async def _safe_delete_file(cls, path: str):
        """P0: Safe non-blocking file deletion."""
        try:
            exists = await cls._run_blocking_io(os.path.exists, path)
            if exists:
                await cls._run_blocking_io(os.remove, path)
                logger.debug(f"Deleted file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {path}: {e}")

    async def _safe_update_acl(self, connector_id: UUID, acl: list, config: dict):
        """Supervised background ACL update."""
        try:
            ai_provider = config.get("ai_provider")
            collection = await self.vector_service.get_collection_name(provider=ai_provider)

            client = await self.vector_service.get_async_qdrant_client()
            repo = VectorRepository(client)
            await repo.update_acl(collection, "connector_id", str(connector_id), acl)

            logger.info(f"BACKGROUND ACL UPDATED | Connector: {connector_id}")
        except Exception as e:
            # P0: Ignore 404/Not Found errors. This happens if the connector is new and hasn't been vectorized yet.
            # The collection (or points) don't exist, so there's nothing to update. Safe to ignore.
            error_msg = str(e).lower()
            if "not found" in error_msg or "doesn't exist" in error_msg or "404" in error_msg:
                logger.debug(
                    f"BACKGROUND ACL SKIPPED | Connector: {connector_id} | Collection not found (Not vectorized yet)"
                )
                return

            logger.error(f"BACKGROUND ACL FAIL | Connector: {connector_id} | Error: {e}")

    async def _safe_delete_vectors(self, connector_id: UUID, config: dict):
        """Supervised background vector deletion."""
        try:
            ai_provider = config.get("ai_provider")
            collection = await self.vector_service.get_collection_name(provider=ai_provider)

            client = await self.vector_service.get_async_qdrant_client()
            repo = VectorRepository(client)
            await repo.delete_by_connector_id(collection, connector_id)

            logger.info(f"BACKGROUND VECTOR CLEANUP SUCCESS | Connector: {connector_id}")
        except Exception as e:
            logger.error(f"BACKGROUND VECTOR CLEANUP FAIL | Connector: {connector_id} | Error: {e}")

    async def _safe_background_scan(self, connector_id: UUID, config: dict):
        """Supervised background scan with fresh DB session."""
        try:
            async with SessionLocal() as db:
                recursive = config.get("recursive", False)

                path = translate_host_path(config.get("path"))
                if not path:
                    logger.warning(f"BACKGROUND SCAN | No path found for {connector_id}")
                    return

                scanner = ScannerService(db)

                # Log Sync Start (Background)
                repo = ConnectorSyncLogRepository(db)
                sync_log = await repo.create_log(connector_id)

                try:
                    stats = await scanner.scan_folder(connector_id, path, recursive=recursive)
                    logger.info(f"BACKGROUND SCAN SUCCESS | Connector: {connector_id}")

                    # Log Sync Success
                    total = stats.get("added", 0) + stats.get("updated", 0)
                    await repo.update_log(sync_log.id, status="success", documents_synced=total)

                except Exception as e:
                    # Log Sync Failure
                    logger.error(f"BACKGROUND SCAN INNER ERROR | {e}")
                    await repo.update_log(sync_log.id, status="failure", error_message=str(e))
                    raise
        except Exception as e:
            logger.error(f"BACKGROUND SCAN FAIL | Connector: {connector_id} | Error: {e}")


# 🟠 P1: Modern FastAPI dependency injection
async def get_connector_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    sql_discovery_service: Annotated[SQLDiscoveryService, Depends(get_sql_discovery_service)],
) -> ConnectorService:
    """Dependency provider for ConnectorService."""
    return ConnectorService(
        connector_repo=ConnectorRepository(db),
        scanner_service=ScannerService(db),
        vector_service=vector_service,
        settings_service=settings_service,
        sql_discovery_service=sql_discovery_service,
    )
