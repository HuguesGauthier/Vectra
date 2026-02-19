"""
Analytics Repository.
Handles complex aggregation queries for the Analytics Dashboard.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.assistant import Assistant
from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.topic_stat import TopicStat
from app.models.usage_stat import UsageStat

# Late import models to avoid circular deps if necessary, or just rely on models being loaded
# from app.models.chat_history import ChatHistory

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """
    Repository for Analytics Data Access.

    ARCHITECT NOTE:
    Encapsulates raw SQL and complex aggregations to keep Services clean.
    Ensures P0 Security via parameterized queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_ttft_percentiles(self, cutoff: datetime) -> Optional[Dict[str, float]]:
        """Calculate TTFT percentiles."""
        try:
            query = select(
                func.percentile_cont(0.50).within_group(UsageStat.ttft).label("p50"),
                func.percentile_cont(0.95).within_group(UsageStat.ttft).label("p95"),
                func.percentile_cont(0.99).within_group(UsageStat.ttft).label("p99"),
            ).where(UsageStat.timestamp > cutoff, UsageStat.ttft.isnot(None))

            result = await self.db.execute(query)
            row = result.first()

            if row and row.p50 is not None:
                return {"p50": float(row.p50), "p95": float(row.p95 or 0), "p99": float(row.p99 or 0)}
            return None
        except SQLAlchemyError as e:
            logger.error(f"TTFT query failed: {e}")
            return None

    async def get_step_breakdown(self, cutoff: datetime) -> List[Any]:
        """Get step breakdown raw rows."""
        try:
            query = text(
                """
                SELECT 
                    step_key as step_name,
                    AVG((step_value)::float) as avg_duration,
                    COUNT(*) as step_count,
                    AVG(NULLIF(step_token_breakdown->step_key->>'input_tokens', '')::float) as avg_input_tokens,
                    AVG(NULLIF(step_token_breakdown->step_key->>'output_tokens', '')::float) as avg_output_tokens
                FROM usage_stats,
                     jsonb_each_text(step_duration_breakdown) as steps(step_key, step_value)
                WHERE timestamp > :cutoff
                  AND step_duration_breakdown IS NOT NULL
                  AND step_key != 'cache_hit'
                GROUP BY step_key
            """
            )
            result = await self.db.execute(query, {"cutoff": cutoff})
            return result.all()
        except SQLAlchemyError as e:
            logger.error(f"Step breakdown query failed: {e}")
            return []

    async def get_cache_stats(self, cutoff: datetime) -> Optional[Any]:
        """Get cache hits/misses."""
        try:
            query = text(
                """
                SELECT 
                    COUNT(*) FILTER (WHERE step_duration_breakdown->>'cache_hit' = 'true') as cache_hits,
                    COUNT(*) as total_requests
                FROM usage_stats
                WHERE timestamp > :cutoff
            """
            )
            result = await self.db.execute(query, {"cutoff": cutoff})
            return result.first()
        except SQLAlchemyError as e:
            logger.error(f"Cache stats query failed: {e}")
            return None

    async def get_trending_topics(self, limit: int, assistant_id: Optional[UUID] = None) -> List[TopicStat]:
        """Get top topics."""
        try:
            query = select(TopicStat).order_by(TopicStat.frequency.desc()).limit(limit)
            if assistant_id:
                query = query.where(TopicStat.assistant_id == assistant_id)

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Trending topics query failed: {e}")
            return []

    async def get_topic_frequencies(self, assistant_id: Optional[UUID] = None) -> List[Any]:
        """Get list of frequencies for diversity calc."""
        try:
            query = select(TopicStat.frequency)
            if assistant_id:
                query = query.where(TopicStat.assistant_id == assistant_id)

            result = await self.db.execute(query)
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"Topic frequencies query failed: {e}")
            return []

    async def get_assistant_usage_sums(self, cutoff: datetime) -> List[Any]:
        """Get token sums per assistant."""
        try:
            query = (
                select(
                    Assistant.id,
                    Assistant.name,
                    func.sum(UsageStat.input_tokens).label("input_tokens"),
                    func.sum(UsageStat.output_tokens).label("output_tokens"),
                    (func.sum(UsageStat.input_tokens) + func.sum(UsageStat.output_tokens)).label("total_tokens"),
                    func.sum(UsageStat.cost).label("cost"),
                )
                .join(UsageStat, UsageStat.assistant_id == Assistant.id)
                .where(UsageStat.timestamp > cutoff)
                .group_by(Assistant.id, Assistant.name)
            )
            result = await self.db.execute(query)
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"Assistant usage query failed: {e}")
            return []

    async def get_document_freshness_stats(self, threshold_30d: datetime, threshold_90d: datetime) -> List[Any]:
        """Get document freshness buckets."""
        try:
            query = select(
                case(
                    (ConnectorDocument.updated_at > threshold_30d, "Fresh (<30d)"),
                    (ConnectorDocument.updated_at > threshold_90d, "Aging (30-90d)"),
                    else_="Stale (>90d)",
                ).label("freshness_category"),
                func.count().label("doc_count"),
            ).group_by("freshness_category")

            result = await self.db.execute(query)
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"Document freshness query failed: {e}")
            return []

    async def get_session_counts(self, cutoff: datetime) -> List[Any]:
        """Get session question counts."""
        try:
            query = text(
                """
                SELECT session_id, COUNT(*) as q_count
                FROM chat_history
                WHERE role = 'user' AND created_at > :cutoff
                GROUP BY session_id
            """
            )
            result = await self.db.execute(query, {"cutoff": cutoff})
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"Session counts query failed: {e}")
            return []

    async def get_document_retrieval_stats(self, cutoff: datetime, limit: int = 50) -> List[Any]:
        """Get enriched document utilization."""
        try:
            # We join with ConnectorDocument and Connector to get human readable names
            query = text(
                """
                SELECT
                    cd.file_name as file_name,
                    c.name as connector_name,
                    COUNT(DISTINCT us.id) as retrieval_count,
                    MAX(us.timestamp) as last_retrieved
                FROM usage_stats us
                CROSS JOIN LATERAL jsonb_array_elements_text(us.step_duration_breakdown->'retrieved_document_ids') AS doc_id
                JOIN connectors_documents cd ON cd.id = (doc_id)::uuid
                JOIN connectors c ON c.id = cd.connector_id
                WHERE us.timestamp > :cutoff
                  AND us.step_duration_breakdown ? 'retrieved_document_ids'
                GROUP BY cd.file_name, c.name
                ORDER BY retrieval_count DESC
                LIMIT :limit
            """
            )
            result = await self.db.execute(query, {"cutoff": cutoff, "limit": limit})
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"Document utilization query failed: {e}")
            return []

    async def get_reranking_stats(self, cutoff: datetime) -> Optional[Any]:
        """Get reranking stats."""
        try:
            query = text(
                """
                SELECT
                    AVG((step_duration_breakdown->>'reranking_impact')::float) as avg_improvement,
                    COUNT(*) as reranking_count
                FROM usage_stats
                WHERE timestamp > :cutoff
                  AND step_duration_breakdown ? 'reranking_impact'
            """
            )
            result = await self.db.execute(query, {"cutoff": cutoff})
            return result.first()
        except SQLAlchemyError as e:
            logger.error(f"Reranking stats query failed: {e}")
            return None

    async def get_connector_sync_stats(self, cutoff: datetime) -> List[Any]:
        """Get connector sync logs."""
        try:
            from app.models.connector_sync_log import ConnectorSyncLog

            query = (
                select(
                    Connector.id,
                    Connector.name,
                    func.count(ConnectorSyncLog.id).label("total_syncs"),
                    func.count(ConnectorSyncLog.id)
                    .filter(ConnectorSyncLog.status == "success")
                    .label("successful_syncs"),
                    func.count(ConnectorSyncLog.id).filter(ConnectorSyncLog.status == "failure").label("failed_syncs"),
                    func.avg(ConnectorSyncLog.sync_duration).label("avg_duration"),
                )
                .join(ConnectorSyncLog, ConnectorSyncLog.connector_id == Connector.id, isouter=True)
                .where((ConnectorSyncLog.sync_time > cutoff) | (ConnectorSyncLog.sync_time.is_(None)))
                .group_by(Connector.id, Connector.name)
            )
            result = await self.db.execute(query)
            return list(result.all())
        except (ImportError, SQLAlchemyError) as e:
            logger.error(f"Connector sync stats query failed: {e}")
            return []

    async def get_user_usage_stats(self, cutoff: datetime, limit: int = 10) -> List[Any]:
        """Get aggregated usage stats per user."""
        try:
            from app.models.user import User

            query = (
                select(
                    User.id.label("user_id"),
                    User.email,
                    User.first_name,
                    User.last_name,
                    func.sum(UsageStat.input_tokens + UsageStat.output_tokens).label("total_tokens"),
                    func.count(UsageStat.id).label("interaction_count"),
                    func.max(UsageStat.timestamp).label("last_active"),
                )
                .join(UsageStat, UsageStat.user_id == User.id)
                .where(UsageStat.timestamp > cutoff)
                .group_by(User.id, User.email, User.first_name, User.last_name)
                .order_by(func.sum(UsageStat.input_tokens + UsageStat.output_tokens).desc())
                .limit(limit)
            )

            result = await self.db.execute(query)
            return list(result.all())
        except SQLAlchemyError as e:
            logger.error(f"User usage stats query failed: {e}")
            return []
