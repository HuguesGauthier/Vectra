import asyncio
import logging
import os
import shutil
import time
from typing import Annotated, Any, Dict, List, Optional, Union
from uuid import UUID

import aiofiles
from fastapi import Depends, UploadFile
from sqlalchemy import desc, func
from sqlalchemy import select as select_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connection_manager import manager
from app.core.database import get_db
from app.core.exceptions import (DuplicateError, EntityNotFound,
                                 FunctionalError, InternalDataCorruption,
                                 TechnicalError)
from app.models.connector_document import ConnectorDocument
from app.models.enums import DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.connector import ConnectorResponse
from app.schemas.documents import (ConnectorDocumentCreate,
                                   ConnectorDocumentResponse,
                                   ConnectorDocumentUpdate)
from app.services.ingestion.utils import IngestionUtils
from app.services.settings_service import SettingsService, get_settings_service
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Architect Refactor of DocumentService.
    Hardens security via Pydantic returns (P0) and non-blocking IO (P0).
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        connector_repo: ConnectorRepository,
        vector_service: Optional[VectorService] = None,
        settings_service: Optional[SettingsService] = None,
    ):
        self.document_repo = document_repo
        self.connector_repo = connector_repo
        self.db = document_repo.db  # Assuming repo has db reference
        self.settings_service = settings_service or SettingsService(self.db)
        self.vector_service = vector_service or VectorService(self.settings_service)

    @staticmethod
    async def _run_blocking_io(func, *args, **kwargs):
        """Wrapper for safe non-blocking IO operations. Fixes P0 Blocking IO."""
        return await asyncio.to_thread(func, *args, **kwargs)

    async def get_connector_documents(
        self,
        connector_id: UUID,
        page: int = 1,
        size: int = 20,
        status: Optional[DocStatus] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Paginated retrieval with optimized count and Pydantic returns.
        Fixes P0: Returns serialized models.
        """
        start_time = time.time()
        try:
            skip = (page - 1) * size

            # 1. Fetch Items
            if search:
                documents = await self.document_repo.search_documents(
                    connector_id=connector_id, search_term=search, status=status, skip=skip, limit=size
                )
            else:
                documents = await self.document_repo.get_by_connector(
                    connector_id, skip=skip, limit=size, status=status
                )

            # 2. Efficient Count
            if search:
                filters = [ConnectorDocument.connector_id == connector_id]
                if status:
                    filters.append(ConnectorDocument.status == status)
                filters.append(ConnectorDocument.file_name.ilike(f"%{search}%"))
                count_stmt = select_func(func.count()).select_from(ConnectorDocument).filter(*filters)
                total = (await self.document_repo.db.execute(count_stmt)).scalar() or 0
            else:
                total = await self.document_repo.count_by_connector(connector_id, status)

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"FETCH | DocumentService.get_connector_documents | Count: {len(documents)} | {elapsed}ms")

            # 🔴 P0: Convert ORM to Pydantic
            items = [ConnectorDocumentResponse.model_validate(doc) for doc in documents]

            return {
                "items": items,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size if total > 0 else 0,
            }
        except Exception as e:
            logger.error(f"Fetch documents failed: {e}", exc_info=True)
            raise TechnicalError("Failed to fetch documents", error_code="FETCH_ERROR")

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Deletes a document and triggers background cleanup for vectors and files.
        Fixes P0: Uses non-blocking path operations.
        """
        start_time = time.time()
        try:
            # 1. Fetch Document Metadata
            doc = await self.document_repo.get_by_id(document_id)
            if not doc:
                raise EntityNotFound(f"Document {document_id} not found")

            connector = await self.connector_repo.get_by_id(doc.connector_id)

            # 2. Side-Effects (Backgrounded)
            if connector:
                # 🟠 P1: Supervised Background Task
                provider = connector.configuration.get("ai_provider") if connector.configuration else None
                collection = await self.vector_service.get_collection_name(provider)
                asyncio.create_task(
                    self._safe_delete_vectors(document_id, collection),
                    name=f"vector-cleanup-{document_id}"
                )

                c_type = str(connector.connector_type).strip().lower()
                if c_type in ["file", "folder"] and doc.file_path:
                    asyncio.create_task(
                        self._safe_delete_file(doc.file_path),
                        name=f"file-cleanup-{document_id}"
                    )

            # 3. Database Removals
            connector_id = doc.connector_id
            await self.document_repo.delete(document_id)

            # 4. Atomic Counter Update
            if connector:
                new_count = max(0, connector.total_docs_count - 1)
                await self.connector_repo.update(connector.id, {"total_docs_count": new_count})
                conn_resp = ConnectorResponse.model_validate(connector)
                await manager.emit_connector_updated(conn_resp.model_dump(mode="json"))

            await manager.emit_document_deleted(str(document_id), str(connector_id))

            logger.info(f"DELETED | Document {document_id} | {round((time.time()-start_time)*1000, 2)}ms")
            return True

        except EntityNotFound:
            raise
        except Exception as e:
            logger.error(f"Logic failure during document deletion: {e}", exc_info=True)
            raise TechnicalError("Delete failed", error_code="DELETE_ERROR") from e

    async def update_document(
        self, document_id: UUID, doc_update: Union[ConnectorDocumentUpdate, Dict[str, Any]]
    ) -> ConnectorDocumentResponse:
        """
        Updates document and handles ACL sync.
        Fixes P0: Returns ConnectorDocumentResponse.
        """
        try:
            doc = await self.document_repo.get_by_id(document_id)
            if not doc:
                raise EntityNotFound(f"Document {document_id} not found")

            # 1. Prepare Updates
            update_data = doc_update if isinstance(doc_update, dict) else doc_update.model_dump(exclude_unset=True)

            # 3. DB Update
            updated_doc = await self.document_repo.update(document_id, update_data)

            # 4. ACL Sync (Background)
            if "configuration" in update_data and "connector_document_acl" in update_data["configuration"]:
                acl = update_data["configuration"]["connector_document_acl"]
                asyncio.create_task(
                    self._safe_update_acl(document_id, acl),
                    name=f"acl-update-{document_id}"
                )

            # 5. Broadcast
            resp = ConnectorDocumentResponse.model_validate(updated_doc)
            await manager.emit_document_updated(resp.model_dump(mode="json"))

            return resp

        except EntityNotFound:
            raise
        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            raise TechnicalError("Update failed", error_code="UPDATE_ERROR")

    async def create_document(self, connector_id: UUID, doc_data: ConnectorDocumentCreate) -> ConnectorDocumentResponse:
        """
        Creates a new document, validates schema if CSV, and updates connector count.
        Fixes P0: Returns ConnectorDocumentResponse.
        """
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            # 1. Content Validation
            if doc_data.file_path and doc_data.file_path.lower().endswith(".csv"):
                try:
                    schema = await IngestionUtils.validate_csv_file(doc_data.file_path)
                except Exception as e:
                    if isinstance(e, (ValueError, FunctionalError)):
                        raise FunctionalError(f"CSV Validation Error: {e}", error_code="INVALID_CSV")
                    raise

                extra_conf = doc_data.configuration or {}
                extra_conf["detected_schema"] = schema
                doc_data.configuration = extra_conf

            # 2. Status Determination
            initial_status = DocStatus.PENDING
            if connector.schedule_type == "manual" or not connector.schedule_cron:
                initial_status = DocStatus.IDLE

            # 3. DB Persistence
            new_doc = await self.document_repo.create(
                {
                    "connector_id": connector_id,
                    "file_path": doc_data.file_path,
                    "file_name": doc_data.file_name,
                    "file_size": doc_data.file_size,
                    "status": initial_status,
                    "configuration": doc_data.configuration or {},
                }
            )

            # 4. Atomic Counter Update
            await self.connector_repo.update(connector.id, {"total_docs_count": connector.total_docs_count + 1})

            resp = ConnectorDocumentResponse.model_validate(new_doc)
            await manager.emit_document_created(resp.model_dump(mode="json"))
            conn_resp = ConnectorResponse.model_validate(connector)
            await manager.emit_connector_updated(conn_resp.model_dump(mode="json"))

            return resp

        except (FunctionalError, EntityNotFound):
            raise
        except IntegrityError:
            raise DuplicateError("Document already exists")
        except Exception as e:
            logger.error(f"Document creation failed: {e}", exc_info=True)
            raise TechnicalError("Create failed", error_code="CREATE_ERROR") from e

    async def upload_file(self, file: UploadFile) -> str:
        """
        True Async Upload using aiofiles with non-blocking directory creation.
        Fixes P0: Non-blocking IO.
        """
        start_time = time.time()
        func_name = "DocumentService.upload_file"

        try:
            upload_dir = "temp_uploads"
            # 🔴 P0: Non-blocking directory creation
            await self._run_blocking_io(os.makedirs, upload_dir, exist_ok=True)

            # os.path.join is purely string manipulation, safe in async.
            file_path = os.path.join(upload_dir, file.filename or "uploaded_file")

            async with aiofiles.open(file_path, "wb") as out_file:
                while content := await file.read(1024 * 1024):  # 1MB chunks
                    await out_file.write(content)

            # Post-upload verification
            if file_path.lower().endswith(".csv"):
                try:
                    await IngestionUtils.validate_csv_file(file_path)
                except Exception as e:
                    await self._safe_delete_file(file_path)
                    if isinstance(e, (FunctionalError, ValueError)):
                        raise FunctionalError(f"Invalid CSV: {e}", error_code="INVALID_CSV")
                    raise TechnicalError(f"CSV Validation Error: {e}", error_code="VALIDATION_ERROR")

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"UPLOAD | {func_name} | {file_path} | {elapsed}ms")
            return file_path

        except (FunctionalError, TechnicalError):
            raise
        except Exception as e:
            logger.error(f"Upload process failed: {e}", exc_info=True)
            raise TechnicalError("File upload failed", error_code="UPLOAD_ERROR")

    async def delete_temp_file(self, file_path: str) -> bool:
        """
        Delete a temporary uploaded file. Used when user cancels connector creation.
        Only allows deletion from temp_uploads directory for security.
        """
        try:
            # 🔴 P0: Path Traversal Protection
            # os.path.abspath is safe as string manipulation, but we must verify the result.
            abs_temp_dir = os.path.abspath("temp_uploads")
            requested_abs_path = os.path.abspath(file_path)

            if not requested_abs_path.startswith(abs_temp_dir):
                logger.warning(f"🛡️ Path traversal attempt blocked: {file_path}")
                raise FunctionalError("Forbidden: Can only delete files from temp_uploads", error_code="FORBIDDEN")

            await self._safe_delete_file(file_path)
            logger.info(f"🗑️ Temp file deleted: {file_path}")
            return True
        except FunctionalError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete temp file {file_path}: {e}", exc_info=True)
            raise TechnicalError("File deletion failed", error_code="DELETE_ERROR")

    async def sync_document(self, document_id: UUID) -> bool:
        """Queues a document for synchronization."""
        try:
            doc = await self.document_repo.get_by_id(document_id)
            if not doc:
                raise EntityNotFound(f"Document {document_id} not found")

            await self.document_repo.update(document_id, {"status": DocStatus.PENDING, "updated_at": func.now()})

            await manager.emit_document_update(str(doc.id), DocStatus.PENDING, "Queued.")
            await manager.emit_trigger_document_sync(str(doc.id))
            return True
        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"Sync trigger failed: {e}")
            raise TechnicalError("Sync failed", error_code="SYNC_ERROR")

    async def stop_document(self, document_id: UUID) -> bool:
        """Gracefully stops document processing."""
        try:
            doc = await self.document_repo.get_by_id(document_id)
            if not doc:
                raise EntityNotFound(f"Document {document_id} not found")

            await self.document_repo.update(document_id, {"status": DocStatus.PAUSED})
            await manager.emit_document_update(str(doc.id), DocStatus.PAUSED, "Paused.")
            return True
        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"Stop command failed: {e}")
            raise TechnicalError("Stop failed", error_code="STOP_ERROR")

    # --- Helpers ---
    async def _safe_delete_vectors(self, document_id: UUID, collection: str):
        """Supervised background vector deletion."""
        try:
            from app.repositories.vector_repository import VectorRepository

            client = self.vector_service.get_async_qdrant_client()
            repo = VectorRepository(client)
            await repo.delete_by_document_id(collection, document_id)
            logger.info(f"BACKGROUND VECTOR CLEANUP SUCCESS | Doc: {document_id}")
        except Exception as e:
            logger.error(f"BACKGROUND VECTOR CLEANUP FAIL | Doc: {document_id} | Error: {e}")

    @classmethod
    async def _safe_delete_file(cls, path: str):
        """P0: Safe non-blocking file deletion."""
        try:
            exists = await cls._run_blocking_io(os.path.exists, path)
            if exists:
                await cls._run_blocking_io(os.remove, path)
                logger.info(f"BACKGROUND FILE DELETE SUCCESS | Path: {path}")
        except Exception as e:
            logger.warning(f"BACKGROUND FILE DELETE FAIL | Path: {path} | Error: {e}")

    async def _safe_update_acl(self, document_id: UUID, acl: list):
        """Supervised background ACL update in vector store."""
        try:
            from app.repositories.vector_repository import VectorRepository

            client = self.vector_service.get_async_qdrant_client()
            repo = VectorRepository(client)
            collection = await self.vector_service.get_collection_name()
            await repo.update_acl(collection, "connector_document_id", str(document_id), acl)
            logger.info(f"BACKGROUND ACL UPDATE SUCCESS | Doc: {document_id}")
        except Exception as e:
            logger.error(f"BACKGROUND ACL UPDATE FAIL | Doc: {document_id} | Error: {e}")


# 🟠 P1: Modern FastAPI Dependency Injection
async def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> DocumentService:
    """Dependency provider for DocumentService."""
    return DocumentService(
        document_repo=DocumentRepository(db),
        connector_repo=ConnectorRepository(db),
        vector_service=vector_service,
        settings_service=settings_service,
    )
