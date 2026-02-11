import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFound, TechnicalError
from app.core.interfaces.base_connector import get_full_path_from_connector
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class SystemService:
    """
    Hardened SystemService.
    Fixes P0 Arbitrary File Access via path whitelisting.
    Fixes P0 Async Blocking via thread-pool offloading.
    """

    def __init__(self, allowed_base_paths: Optional[List[str]] = None, db: Optional[AsyncSession] = None):
        # Default to the project root and temporary directory for safety
        project_root = Path(__file__).parent.parent.parent.parent.resolve()
        self.allowed_base_paths = [project_root, Path(os.environ.get("TEMP", "/tmp")).resolve()]
        if allowed_base_paths:
            self.allowed_base_paths.extend([Path(p).resolve() for p in allowed_base_paths])

        self.db = db

    def _is_safe_path(self, path: Path) -> bool:
        """Checks if a path is within the allowed base directories."""
        try:
            resolved_path = path.resolve()
            return any(resolved_path == base or base in resolved_path.parents for base in self.allowed_base_paths)
        except (ValueError, RuntimeError):
            return False

    async def open_file_by_document_id(self, document_id: str) -> bool:
        """
        Open a file by its document ID.
        Reconstructs the full path using connector configuration and document file_path.

        Args:
            document_id: UUID of the ConnectorDocument

        Returns:
            True if file was opened successfully

        Raises:
            EntityNotFound: If document or connector not found
            TechnicalError: If path reconstruction or file opening fails
        """
        if not self.db:
            raise TechnicalError("Database session not available")

        try:
            doc_id = UUID(document_id)

            # Fetch document
            doc_repo = DocumentRepository(self.db)
            doc = await doc_repo.get_by_id(doc_id)
            if not doc:
                raise EntityNotFound(f"Document {document_id} not found")

            # Fetch connector
            conn_repo = ConnectorRepository(self.db)
            connector = await conn_repo.get_by_id(doc.connector_id)
            if not connector:
                raise EntityNotFound(f"Connector not found for document {document_id}")

            # Reconstruct full path using helper
            full_path = get_full_path_from_connector(connector, doc.file_path)

            # Open the file
            return await self.open_file_externally(full_path)

        except (EntityNotFound, TechnicalError):
            raise
        except ValueError as e:
            raise TechnicalError(f"Invalid document ID format: {e}")
        except Exception as e:
            logger.error(f"Failed to open file by document ID: {e}", exc_info=True)
            raise TechnicalError(f"System error while opening file: {e}")

    async def open_file_externally(self, path: str) -> bool:
        """
        Opens a file using the host OS default application.
        Ensures non-blocking execution and security boundaries.
        """
        try:
            file_path = Path(path).resolve()

            # 1. Path Safety Check
            if not self._is_safe_path(file_path):
                logger.error(f"Unauthorized path access blocked: {file_path}")
                raise TechnicalError(
                    message="Unauthorized path access blocked for security reasons.",
                    error_code="UNAUTHORIZED_PATH_ACCESS",
                )

            if not file_path.exists():
                raise EntityNotFound(f"File not found: {path}")

            # 2. Platform Specific Execution (P0: Non-blocking)
            return await asyncio.to_thread(self._open_sync, file_path)

        except (EntityNotFound, TechnicalError):
            raise
        except Exception as e:
            logger.error(f"Failed to open file externally: {e}", exc_info=True)
            raise TechnicalError(f"System error while opening file: {e}")

    def _open_sync(self, file_path: Path) -> bool:
        """Actual platform-specific open logic (run in thread)."""
        if sys.platform == "win32":
            os.startfile(str(file_path))
        elif sys.platform == "darwin":
            subprocess.call(["open", str(file_path)])
        else:
            subprocess.call(["xdg-open", str(file_path)])

        logger.info(f"Opened file externally: {file_path}")
        return True


def get_system_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SystemService:
    """Dependency provider for SystemService."""
    return SystemService(db=db)
