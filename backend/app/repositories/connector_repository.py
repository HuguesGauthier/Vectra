"""
Connector Repository - DB Access for Connectors.

ARCHITECT NOTE:
This repository manages Connector entities and their complex relationships.
It implements bulk aggregation logic to avoid N+1 queries when fetching status.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.assistant import AssistantConnectorLink
from app.models.connector import Connector, ConnectorStatus
from app.models.connector_document import ConnectorDocument
from app.repositories.base_repository import DEFAULT_LIMIT, MAX_LIMIT
from app.repositories.sql_repository import SQLRepository

logger = logging.getLogger(__name__)


class ConnectorRepository(SQLRepository[Connector, Any, Any]):
    """
    Handles persistence logic for Connectors.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Connector, db)

    async def get_all_with_stats(self, skip: int = 0, limit: int = DEFAULT_LIMIT) -> List[Connector]:
        """
        Fetch connectors with their latest vectorization date.

        ARCHITECT NOTE: N+1 Prevention
        Instead of querying last_vectorized_at for each connector in a loop,
        we perform a single bulk aggregation query and merge in memory.
        """
        # DoS Prevention
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        try:
            # 1. Fetch Connectors with pagination
            stmt = select(Connector).order_by(desc(Connector.created_at)).offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            connectors = list(result.scalars().all())

            if not connectors:
                return []

            # 2. Bulk Fetch Max Dates (Efficient Aggregation)
            connector_ids = [c.id for c in connectors]
            doc_max_query = (
                select(
                    ConnectorDocument.connector_id,
                    func.max(ConnectorDocument.last_vectorized_at).label("max_vectorized_at"),
                )
                .where(ConnectorDocument.connector_id.in_(connector_ids))
                .group_by(ConnectorDocument.connector_id)
            )
            doc_result = await self.db.execute(doc_max_query)

            # Map results to dict for O(1) lookup
            doc_max_dates = {row.connector_id: row.max_vectorized_at for row in doc_result}

            # 3. Merge in memory
            # NOTE: last_vectorized_at is a dynamic property, not persisted in Connector table directly
            for connector in connectors:
                connector.last_vectorized_at = doc_max_dates.get(connector.id)

            return connectors

        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch connectors with stats: {e}")
            raise TechnicalError(f"Database error during stats aggregation: {e}")

    async def delete_with_relations(self, connector_id: UUID) -> bool:
        """
        Delete connector and all related entities atomically.

        ARCHITECT NOTE: Transaction Integrity
        A failure during relation deletion would leave orphaned records.
        This method ensures full rollback on any failure.
        """
        try:
            # 1. Verify existence
            exists = await self.exists(connector_id)
            if not exists:
                return False

            # 2. Delete relations (Manual Cascade)
            # We explicitly delete to avoid relying solely on DB triggers for complex logic
            await self.db.execute(delete(ConnectorDocument).where(ConnectorDocument.connector_id == connector_id))
            await self.db.execute(
                delete(AssistantConnectorLink).where(AssistantConnectorLink.connector_id == connector_id)
            )

            # 3. Delete Connector
            # Note: We use the base class delete which handles the commit if needed,
            # but here we want to ensure everything is in one transaction.
            # SQLRepository.delete calls db.commit(), so we are safe assuming
            # the sequence of operations is logical.
            success = await self.delete(connector_id)

            logger.info(f"Successfully deleted connector {connector_id} and all related records.")
            return success

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Atomic deletion failed for connector {connector_id}: {e}")
            raise TechnicalError(f"Failed to delete connector and relations: {e}")

    async def get_by_statuses(self, statuses: List[ConnectorStatus]) -> List[Connector]:
        """
        Fetch all connectors matching specific statuses using Enum type safety.
        """
        try:
            # SQLAlchemy handles StrEnum automatically
            query = select(Connector).where(Connector.status.in_(statuses))
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch connectors by status: {e}")
            raise TechnicalError(f"Database error during status query: {e}")
