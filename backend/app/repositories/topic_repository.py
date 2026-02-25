"""
Topic Repository - DB Access for Trending Topics.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.topic_stat import TopicStat
from app.schemas.topic_stat import TopicStatCreate, TopicStatUpdate
from app.repositories.base_repository import DEFAULT_LIMIT, MAX_LIMIT
from app.repositories.sql_repository import SQLRepository

logger = logging.getLogger(__name__)


class TopicRepository(SQLRepository[TopicStat, TopicStatCreate, TopicStatUpdate]):
    """
    Repository for managing Topic Statistics.

    ARCHITECT NOTE: Analytics & Locking
    Provides specialized methods for trending analysis and atomic updates via row locking.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(TopicStat, db)

    async def get_by_id_with_lock(self, topic_id: UUID) -> Optional[TopicStat]:
        """
        Fetch topic with row-level locking for atomic updates.

        Args:
            topic_id: UUID of the topic.

        Returns:
            Locked TopicStat or None.

        Raises:
            TechnicalError: If database locking fails.
        """
        try:
            stmt = select(TopicStat).where(TopicStat.id == topic_id).with_for_update()
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Failed to acquire lock for topic {topic_id}: {e}")
            raise TechnicalError(f"Database error acquiring lock: {e}")

    async def get_trending(self, assistant_id: Optional[UUID] = None, limit: int = 10) -> List[TopicStat]:
        """
        Fetch top trending topics ordered by frequency.

        Args:
            assistant_id: Optional filter by assistant.
            limit: Maximum number of topics to return (capped at MAX_LIMIT).

        Returns:
            List of trending topics.
        """
        limit = self._apply_limit(limit)

        try:
            # Only show questions with frequency > 1 (actually trending)
            query = select(TopicStat).where(TopicStat.frequency > 1).order_by(TopicStat.frequency.desc())

            if assistant_id:
                query = query.where(TopicStat.assistant_id == assistant_id)

            query = query.limit(limit)

            result = await self.db.execute(query)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch trending topics: {e}")
            raise TechnicalError(f"Database error fetching trending topics: {e}")
