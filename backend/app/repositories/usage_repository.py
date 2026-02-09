"""
Usage Repository - Analytics data access.

Handles retrieval and aggregation of usage statistics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.usage_stat import UsageStat, UsageStatCreate, UsageStatUpdate
from app.repositories.sql_repository import SQLRepository

logger = logging.getLogger(__name__)


class UsageRepository(SQLRepository[UsageStat, UsageStatCreate, UsageStatUpdate]):
    """
    Repository for Usage Statistics.

    ARCHITECT NOTE: Analytics Engine
    Provides retrieval and aggregation methods for assistant usage data.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(UsageStat, db)

    async def get_daily_usage(self, assistant_id: UUID, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily usage metrics for an assistant.

        Args:
            assistant_id: ID of the assistant.
            days: Number of days to look back.

        Returns:
            List of daily stats (date, count, total_tokens).
        """
        try:
            # P2: Use timezone-aware UTC
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Using func.date(UsageStat.timestamp) for standard SQL (Postgres/SQLite compat)
            stmt = (
                select(
                    func.date(UsageStat.timestamp).label("date"),
                    func.count(UsageStat.id).label("count"),
                    func.sum(UsageStat.input_tokens + UsageStat.output_tokens).label("total_tokens"),
                    func.avg(UsageStat.total_duration).label("avg_duration"),
                )
                .where(
                    and_(
                        UsageStat.assistant_id == assistant_id,
                        UsageStat.timestamp
                        >= cutoff_date.replace(tzinfo=None),  # Handle DB timestamp naivety if necessary
                    )
                )
                .group_by("date")
                .order_by("date")
            )

            result = await self.db.execute(stmt)
            return [
                {
                    "date": row.date,
                    "count": row.count,
                    "total_tokens": row.total_tokens or 0,
                    "avg_duration": row.avg_duration or 0.0,
                }
                for row in result.all()
            ]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get daily usage for assistant {assistant_id}: {e}")
            raise TechnicalError(f"Database error aggregating daily usage: {e}")

    async def get_total_tokens(self, assistant_id: UUID) -> int:
        """Get total tokens sum for an assistant."""
        try:
            stmt = select(func.sum(UsageStat.input_tokens + UsageStat.output_tokens)).where(
                UsageStat.assistant_id == assistant_id
            )
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to get total tokens for assistant {assistant_id}: {e}")
            raise TechnicalError(f"Database error counting tokens: {e}")

    async def get_stats_by_user(self, user_id: UUID, limit: int = 10) -> List[UsageStat]:
        """Get recent usage for a specific user."""
        limit = self._apply_limit(limit)
        try:
            stmt = (
                select(UsageStat).where(UsageStat.user_id == user_id).order_by(UsageStat.timestamp.desc()).limit(limit)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to get stats for user {user_id}: {e}")
            raise TechnicalError(f"Database error fetching user stats: {e}")
