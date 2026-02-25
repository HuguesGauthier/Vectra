"""
Document Repository - Manages ConnectorDocument entity data access.

Extends SQLRepository with document-specific queries including connector filtering,
status filtering, and ACL-based access control.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.connector_document import ConnectorDocument
from app.repositories.base_repository import DEFAULT_LIMIT, MAX_LIMIT
from app.repositories.sql_repository import SQLRepository
from app.schemas.enums import DocStatus

logger = logging.getLogger(__name__)


class DocumentRepository(SQLRepository[ConnectorDocument, Any, Any]):
    """
    Document-specific repository.

    ARCHITECT NOTE: Domain Logic Encapsulation
    All document querying logic is centralized here. Services remain clean.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(ConnectorDocument, db)

    def _apply_limit(self, limit: int) -> int:
        """Capped limit to prevent DoS."""
        if limit > MAX_LIMIT:
            return MAX_LIMIT
        return limit

    async def get_by_connector(
        self, connector_id: UUID, skip: int = 0, limit: int = DEFAULT_LIMIT, status: Optional[DocStatus] = None
    ) -> List[ConnectorDocument]:
        """
        Retrieve documents for a specific connector.

        ARCHITECT NOTE: DoS Protection
        Limit is capped at MAX_LIMIT internally.
        """
        limit = self._apply_limit(limit)
        try:
            statement = select(ConnectorDocument).where(ConnectorDocument.connector_id == connector_id)

            if status:
                statement = statement.where(ConnectorDocument.status == status)

            statement = statement.offset(skip).limit(limit).order_by(ConnectorDocument.created_at.desc())

            result = await self.db.execute(statement)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting documents for connector {connector_id}: {e}")
            raise TechnicalError(f"Failed to fetch documents: {e}")

    async def search_documents(
        self,
        connector_id: Optional[UUID] = None,
        search_term: Optional[str] = None,
        status: Optional[DocStatus] = None,
        skip: int = 0,
        limit: int = DEFAULT_LIMIT,
    ) -> List[ConnectorDocument]:
        """
        Search documents with multiple filter options.
        """
        limit = self._apply_limit(limit)
        try:
            statement = select(ConnectorDocument)

            conditions = []
            if connector_id:
                conditions.append(ConnectorDocument.connector_id == connector_id)

            if search_term:
                conditions.append(
                    or_(
                        ConnectorDocument.file_name.ilike(f"%{search_term}%"),
                        ConnectorDocument.file_path.ilike(f"%{search_term}%"),
                    )
                )

            if status:
                conditions.append(ConnectorDocument.status == status)

            if conditions:
                statement = statement.where(and_(*conditions))

            statement = statement.offset(skip).limit(limit).order_by(ConnectorDocument.created_at.desc())

            result = await self.db.execute(statement)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Database error searching documents: {e}")
            raise TechnicalError(f"Failed to search documents: {e}")

    async def get_by_status(
        self, status: DocStatus, skip: int = 0, limit: int = DEFAULT_LIMIT
    ) -> List[ConnectorDocument]:
        """Get documents by status with pagination."""
        limit = self._apply_limit(limit)
        try:
            statement = (
                select(ConnectorDocument)
                .where(ConnectorDocument.status == status)
                .offset(skip)
                .limit(limit)
                .order_by(ConnectorDocument.created_at.desc())
            )

            result = await self.db.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error getting documents by status {status}: {e}")
            raise TechnicalError(f"Failed to fetch documents by status: {e}")

    async def get_pending_documents(self, limit: int = DEFAULT_LIMIT) -> List[ConnectorDocument]:
        """Get documents pending processing."""
        return await self.get_by_status(DocStatus.PENDING, skip=0, limit=limit)

    async def get_failed_documents(self, limit: int = DEFAULT_LIMIT) -> List[ConnectorDocument]:
        """Get documents that failed processing."""
        return await self.get_by_status(DocStatus.FAILED, skip=0, limit=limit)

    async def count_by_connector(self, connector_id: UUID, status: Optional[DocStatus] = None) -> int:
        """Count documents for a connector."""
        try:
            statement = (
                select(func.count())
                .select_from(ConnectorDocument)
                .where(ConnectorDocument.connector_id == connector_id)
            )

            if status:
                statement = statement.where(ConnectorDocument.status == status)

            result = await self.db.execute(statement)
            return result.scalar_one()

        except SQLAlchemyError as e:
            logger.error(f"Database error counting documents for connector {connector_id}: {e}")
            raise TechnicalError(f"Failed to count documents: {e}")

    async def get_by_file_path(self, connector_id: UUID, file_path: str) -> Optional[ConnectorDocument]:
        """Get document by connector and file path (unique constraint)."""
        try:
            statement = select(ConnectorDocument).where(
                and_(ConnectorDocument.connector_id == connector_id, ConnectorDocument.file_path == file_path)
            )
            result = await self.db.execute(statement)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching document by path {file_path}: {e}")
            raise TechnicalError(f"Failed to fetch document by path: {e}")

    # Alias for backward compatibility
    async def get_by_connector_and_path(self, connector_id: UUID, file_path: str) -> Optional[ConnectorDocument]:
        """Alias for get_by_file_path for backward compatibility."""
        return await self.get_by_file_path(connector_id, file_path)

    async def upsert_connector_documents(self, connector_id: UUID, llama_docs: List[Any]) -> List[ConnectorDocument]:
        """
        Upsert documents from LlamaIndex Documents to database.

        Business logic method that handles:
        - Extracting file_path from LlamaIndex Document metadata
        - Checking for existing documents
        - Creating new or updating existing documents
        - Committing the transaction

        ARCHITECT NOTE: Repository Pattern - Business Logic Encapsulation
        This method encapsulates all document upsert logic.
        IngestionService should NOT have SQL/ORM logic.

        Args:
            connector_id: UUID of the connector
            llama_docs: List of LlamaIndex Document objects with metadata

        Returns:
            List of persisted ConnectorDocument entities

        Raises:
            TechnicalError: If database operation fails
        """
        processed_docs = []

        try:
            for doc in llama_docs:
                # Extract file_path from LlamaIndex metadata
                file_path = doc.metadata.get("file_path") or doc.id_

                # Check if document exists
                existing = await self.get_by_file_path(connector_id, file_path)

                if existing:
                    # Update existing document (Manual UPDATE to keep transaction open)
                    existing.status = DocStatus.INDEXED
                    existing.file_metadata = doc.metadata

                    self.db.add(existing)  # Add to session for flush/commit
                    processed_docs.append(existing)
                    logger.debug(f"Updated existing document: {file_path}")

                else:
                    # Extract file_name with fallback
                    file_name = doc.metadata.get("file_name")
                    if not file_name:
                        file_name = os.path.basename(file_path)

                    # Create new document
                    new_doc = ConnectorDocument(
                        connector_id=connector_id,
                        file_path=file_path,
                        file_name=file_name,
                        status=DocStatus.INDEXED,
                        file_metadata=doc.metadata,
                    )
                    self.db.add(new_doc)
                    processed_docs.append(new_doc)
                    logger.debug(f"Created new document: {file_path}")

            # Commit transaction once for all documents
            await self.db.commit()

            # Refresh all to get generated fields if needed (optional optimization: skip if not needed)
            for doc in processed_docs:
                await self.db.refresh(doc)

            logger.info(f"Upserted {len(processed_docs)} documents for connector {connector_id}")
            return processed_docs

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error upserting documents: {e}", exc_info=True)
            raise TechnicalError(f"Failed to upsert documents: {e}")

    async def update_status(
        self, document_id: UUID, status: DocStatus, error_message: Optional[str] = None
    ) -> Optional[ConnectorDocument]:
        """
        Update document status and optional error message.
        """
        update_data = {"status": status}
        if error_message is not None:
            update_data["error_message"] = error_message

        try:
            return await self.update(document_id, update_data)
        except SQLAlchemyError as e:
            logger.error(f"Failed to update status for document {document_id}: {e}")
            raise TechnicalError(f"Failed to update status: {e}")

    async def get_aggregate_stats(self) -> dict:
        """
        Calculates aggregate statistics for all documents.
        Returns a dict with total_docs, total_tokens, and total_vectors.
        """
        try:
            statement = select(
                func.count(ConnectorDocument.id).label("total_docs"),
                func.sum(ConnectorDocument.doc_token_count).label("total_tokens"),
                func.sum(ConnectorDocument.vector_point_count).label("total_vectors"),
            )

            result = await self.db.execute(statement)
            stats = result.one()

            return {
                "total_docs": stats.total_docs or 0,
                "total_tokens": stats.total_tokens or 0,
                "total_vectors": stats.total_vectors or 0,
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error calculating aggregates: {e}")
            raise TechnicalError(f"Failed to calculate aggregates: {e}")
