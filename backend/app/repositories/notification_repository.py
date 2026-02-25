"""
Notification Repository - Managed secured data access for user notifications.

ARCHITECT NOTE: Secured Multi-tenancy
ALL methods MUST enforce user_id filtering to prevent cross-user data leaks.
"""

import logging
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.notification import Notification
from app.repositories.base_repository import DEFAULT_LIMIT, MAX_LIMIT
from app.repositories.sql_repository import SQLRepository

logger = logging.getLogger(__name__)


class NotificationRepository(SQLRepository[Notification, Any, Any]):
    """
    Handles secured CRUD operations for Notifications.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_by_id_secured(self, user_id: UUID, notification_id: UUID) -> Optional[Notification]:
        """Fetch notification ONLY if owned by the user."""
        try:
            stmt = select(Notification).where(and_(Notification.id == notification_id, Notification.user_id == user_id))
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch notification {notification_id} for user {user_id}: {e}")
            raise TechnicalError(f"Database error during secured fetch: {e}")

    async def get_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = DEFAULT_LIMIT,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
    ) -> List[Notification]:
        """Paginated list fetch scoped to user."""
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        try:
            query = select(Notification).where(Notification.user_id == user_id).order_by(desc(Notification.created_at))

            conditions = []
            if unread_only:
                conditions.append(Notification.read == False)
            if notification_type:
                conditions.append(Notification.type == notification_type)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to list notifications for user {user_id}: {e}")
            raise TechnicalError(f"Database error listing notifications: {e}")

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Batch update read status for a specific user."""
        try:
            stmt = (
                update(Notification)
                .where(and_(Notification.user_id == user_id, Notification.read == False))
                .values(read=True)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to mark notifications as read for user {user_id}: {e}")
            raise TechnicalError(f"Batch update failed: {e}")

    async def clear_all(self, user_id: UUID) -> int:
        """Atomic deletion of user notifications."""
        try:
            stmt = delete(Notification).where(Notification.user_id == user_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to clear notifications for user {user_id}: {e}")
            raise TechnicalError(f"Clear all failed: {e}")

    async def get_unread_count(self, user_id: UUID) -> int:
        """Optimized count query scoped to user."""
        try:
            query = (
                select(func.count())
                .select_from(Notification)
                .where(and_(Notification.user_id == user_id, Notification.read == False))
            )
            result = await self.db.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to get unread count for user {user_id}: {e}")
            raise TechnicalError(f"Count query failed: {e}")
