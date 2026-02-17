"""
Dashboard Statistics Service.

Provides real-time aggregated metrics from the database for Connect, Vectorize, and Chat pipelines.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.usage_stat import UsageStat
from app.schemas.dashboard_stats import ChatStats, ConnectStats, DashboardStats, VectorizeStats
from app.schemas.enums import ConnectorStatus, DocStatus

logger = logging.getLogger(__name__)


class DashboardStatsService:
    """Service for aggregating dashboard statistics from the database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_connect_stats(self) -> ConnectStats:
        """
        Aggregate Connect pipeline statistics from connectors table.

        Returns:
            ConnectStats with active pipelines, total connectors, system status, and last sync.
        """
        try:
            # Query for total connectors and active connectors
            stmt = select(
                func.count(Connector.id).label("total"),
                # Active = Enabled (not just running)
                func.count(Connector.id).filter(Connector.is_enabled == True).label("active"),
                func.max(Connector.last_vectorized_at).label("last_sync"),
                # System Error = Only if FAILED status (ignore old errors)
                func.count(Connector.id).filter(Connector.status == ConnectorStatus.ERROR).label("error_count"),
            )

            result = await self.db.execute(stmt)
            row = result.first()

            if not row:
                return ConnectStats()

            total_connectors = row.total or 0
            active_pipelines = row.active or 0
            last_sync_time = row.last_sync
            error_count = row.error_count or 0

            # System status is "error" if any connector has recent errors
            system_status = "error" if error_count > 0 else "ok"

            from app.core.utils.storage import get_storage_status

            storage_status = "online" if get_storage_status() else "offline"

            return ConnectStats(
                active_pipelines=active_pipelines,
                total_connectors=total_connectors,
                system_status=system_status,
                storage_status=storage_status,
                last_sync_time=last_sync_time,
            )

        except Exception as e:
            logger.error(f"Failed to get connect stats: {e}", exc_info=True)
            return ConnectStats()

    async def get_vectorize_stats(self) -> VectorizeStats:
        """
        Aggregate Vectorize pipeline statistics from connectors_documents table.

        Returns:
            VectorizeStats with total vectors, tokens, success rate, and failed docs.
        """
        try:
            # Query for vectorization metrics
            stmt = select(
                func.coalesce(func.sum(ConnectorDocument.vector_point_count), 0).label("total_vectors"),
                func.coalesce(func.sum(ConnectorDocument.doc_token_count), 0).label("total_tokens"),
                func.count(ConnectorDocument.id).label("total_docs"),
                func.count(ConnectorDocument.id)
                .filter(ConnectorDocument.status == DocStatus.INDEXED)
                .label("indexed_docs"),
                func.count(ConnectorDocument.id)
                .filter(ConnectorDocument.status == DocStatus.FAILED)
                .label("failed_docs"),
            )

            result = await self.db.execute(stmt)
            row = result.first()

            if not row:
                return VectorizeStats()

            total_vectors = int(row.total_vectors or 0)
            total_tokens = int(row.total_tokens or 0)
            total_docs = row.total_docs or 0
            indexed_docs = row.indexed_docs or 0
            failed_docs = row.failed_docs or 0

            # Calculate success rate
            success_rate = (indexed_docs / total_docs) if total_docs > 0 else 0.0

            return VectorizeStats(
                total_vectors=total_vectors,
                total_tokens=total_tokens,
                indexing_success_rate=round(success_rate, 4),
                failed_docs_count=failed_docs,
            )

        except Exception as e:
            logger.error(f"Failed to get vectorize stats: {e}", exc_info=True)
            return VectorizeStats()

    async def get_chat_stats(self) -> ChatStats:
        """
        Aggregate Chat pipeline statistics from usage_stats table.

        Returns:
            ChatStats with monthly sessions, avg TTFT, total tokens, and avg feedback score.
        """
        try:
            # Get date 30 days ago
            thirty_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

            # Query for chat metrics from last 30 days
            stmt = select(
                func.count(func.distinct(UsageStat.session_id)).label("sessions"),
                func.avg(UsageStat.ttft).label("avg_ttft"),
                func.coalesce(func.sum(UsageStat.input_tokens + UsageStat.output_tokens), 0).label("total_tokens"),
            ).where(UsageStat.timestamp >= thirty_days_ago)

            result = await self.db.execute(stmt)
            row = result.first()

            if not row:
                return ChatStats()

            monthly_sessions = row.sessions or 0
            avg_ttft = float(row.avg_ttft or 0.0)
            total_tokens = int(row.total_tokens or 0)

            return ChatStats(
                monthly_sessions=monthly_sessions, avg_latency_ttft=round(avg_ttft, 3), total_tokens_used=total_tokens
            )

        except Exception as e:
            logger.error(f"Failed to get chat stats: {e}", exc_info=True)
            return ChatStats()

    async def get_all_stats(self) -> DashboardStats:
        """
        Aggregate all dashboard statistics.

        Returns:
            DashboardStats containing Connect, Vectorize, and Chat metrics.
        """
        connect_stats = await self.get_connect_stats()
        vectorize_stats = await self.get_vectorize_stats()
        chat_stats = await self.get_chat_stats()

        return DashboardStats(connect=connect_stats, vectorize=vectorize_stats, chat=chat_stats)
