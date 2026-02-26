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

    def _is_safe_path(self, path: Path, additional_allowed_paths: Optional[List[Path]] = None) -> bool:
        """Checks if a path is within the allowed base directories."""
        try:
            resolved_path = path.resolve()

            # Combine default and additional allowed paths
            all_allowed = self.allowed_base_paths[:]
            if additional_allowed_paths:
                all_allowed.extend(additional_allowed_paths)

            return any(resolved_path == base or base in resolved_path.parents for base in all_allowed)
        except (ValueError, RuntimeError):
            return False

    async def get_resolved_path_by_document_id(self, document_id: str) -> Path:
        """
        Resolves the full path of a document by its ID and ensures it's safe.
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
            file_path = Path(full_path).resolve()

            # SECURITY: Extract the connector base path and allow it for this specific operation
            base_path = connector.configuration.get("path")
            additional_allowed = [Path(base_path).resolve()] if base_path else []

            # Path Safety Check
            if not self._is_safe_path(file_path, additional_allowed_paths=additional_allowed):
                logger.error(f"Unauthorized path access blocked: {file_path}")
                raise TechnicalError(
                    message="Unauthorized path access blocked for security reasons.",
                    error_code="UNAUTHORIZED_PATH_ACCESS",
                )

            if not file_path.exists():
                raise EntityNotFound(f"File not found: {full_path}")

            return file_path

        except (EntityNotFound, TechnicalError):
            raise
        except ValueError as e:
            raise TechnicalError(f"Invalid document ID format: {e}")
        except Exception as e:
            logger.error(f"Failed to resolve path for document ID: {e}", exc_info=True)
            raise TechnicalError(f"System error while resolving file path: {e}")

    async def open_file_by_document_id(self, document_id: str) -> bool:
        """
        Open a file by its document ID.
        Reconstructs the full path using connector configuration and document file_path.
        """
        file_path = await self.get_resolved_path_by_document_id(document_id)
        return await self.open_file_externally(str(file_path))

    async def open_file_externally(self, path: str, additional_allowed_paths: Optional[List[Path]] = None) -> bool:
        """
        Opens a file using the host OS default application.
        Ensures non-blocking execution and security boundaries.
        """
        try:
            file_path = Path(path).resolve()

            # Path Safety Check (already done in get_resolved_path_by_document_id if called from there, 
            # but we keep it here for standalone calls to open_file_externally)
            if not self._is_safe_path(file_path, additional_allowed_paths=additional_allowed_paths):
                logger.error(f"Unauthorized path access blocked: {file_path}")
                raise TechnicalError(
                    message="Unauthorized path access blocked for security reasons.",
                    error_code="UNAUTHORIZED_PATH_ACCESS",
                )

            if not file_path.exists():
                raise EntityNotFound(f"File not found: {path}")

            # Platform Specific Execution (P0: Non-blocking)
            return await asyncio.to_thread(self._open_sync, file_path)

        except (EntityNotFound, TechnicalError):
            raise
        except Exception as e:
            logger.error(f"Failed to open file externally: {e}", exc_info=True)
            raise TechnicalError(f"System error while opening file: {e}")

    def _open_sync(self, file_path: Path) -> bool:
        """Actual platform-specific open logic (run in thread)."""
        try:
            if sys.platform == "win32":
                os.startfile(str(file_path))
            elif sys.platform == "darwin":
                subprocess.call(["open", str(file_path)])
            else:
                # Check if xdg-open exists to avoid FileNotFoundError
                import shutil
                if shutil.which("xdg-open"):
                    subprocess.call(["xdg-open", str(file_path)])
                else:
                    logger.warning(f"xdg-open not found. Cannot open {file_path} in headless/container environment.")
                    raise TechnicalError("System opener (xdg-open) not found. This feature is not supported in a containerized environment.")

            logger.info(f"Opened file externally: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error in _open_sync: {e}")
            raise


def get_system_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SystemService:
    """Dependency provider for SystemService."""
    return SystemService(db=db)
