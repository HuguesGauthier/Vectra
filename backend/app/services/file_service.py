import asyncio
import logging
import mimetypes
import os
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFound, TechnicalError
from app.core.interfaces.base_connector import get_full_path_from_connector
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.files import FileStreamingInfo

logger = logging.getLogger(__name__)


class FileService:
    """
    Architect Refactor of FileService.
    Hardens architecture via modern DI (P1) and strict typing (P2).
    """

    def __init__(self, document_repo: DocumentRepository):
        self.document_repo = document_repo

    @staticmethod
    def detect_mime_type(file_path: str) -> str:
        """
        Detects MIME type for a file.
        Wraps standard library logic.
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    async def get_file_for_streaming(self, document_id: UUID) -> FileStreamingInfo:
        """
        Retrieves file path, media type, and filename for headers.
        Fixes P2: Returns a structured Pydantic model instead of an anonymous Tuple.
        """
        try:
            document = await self.document_repo.get_by_id(document_id)

            if not document:
                raise EntityNotFound(f"Document {document_id} not found")

            # 🟠 P1: Cleaned up inline imports to top-level
            connector_repo = ConnectorRepository(self.document_repo.db)
            connector = await connector_repo.get_by_id(document.connector_id)

            if not connector:
                logger.warning(f"CONNECTOR_NOT_FOUND | ConnID: {document.connector_id} | DocID: {document_id}")
                raise EntityNotFound(f"Connector {document.connector_id} not found")

            # Reconstruct full path from connector + relative path
            file_path = get_full_path_from_connector(connector, document.file_path)

            # P0 Check (Already present but kept for safety): Non-blocking IO check
            file_exists = await asyncio.to_thread(os.path.exists, file_path)

            if not file_exists:
                logger.error(f"FILE MISSING | Path: {file_path} | DocID: {document_id}")
                raise EntityNotFound("File resource missing on server")

            media_type = self.detect_mime_type(file_path)

            return FileStreamingInfo(file_path=file_path, media_type=media_type, file_name=document.file_name)

        except EntityNotFound:
            raise
        except Exception as e:
            logger.error(f"STREAMING_FETCH_FAIL | DocID: {document_id} | Error: {e}", exc_info=True)
            raise TechnicalError("Failed to retrieve file for streaming", error_code="FILE_RETRIEVAL_ERROR")


# 🟠 P1: Modern FastAPI Dependency Injection
async def get_file_service(db: Annotated[AsyncSession, Depends(get_db)]) -> FileService:
    """
    Dependency provider for FileService.
    Uses Annotated and injects the repository for better testability.
    """
    return FileService(DocumentRepository(db))
