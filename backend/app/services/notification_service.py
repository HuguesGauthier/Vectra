import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFound, TechnicalError
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate, NotificationResponse

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Architect Refactor of NotificationService.
    Ensures P0 user-scoping (multi-tenancy) and P0 secure data serialization.
    """

    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def get_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
    ) -> List[NotificationResponse]:
        """
        Retrieves notifications with mandatory user_id scoping.
        Fixes P0: Broken user scoping and raw ORM leak.
        """
        try:
            limit = min(limit, 1000)

            notifications = await self.notification_repo.get_notifications(
                user_id=user_id, skip=skip, limit=limit, unread_only=unread_only, notification_type=notification_type
            )

            return [NotificationResponse.model_validate(n) for n in notifications]

        except Exception as e:
            logger.error(f"Failed to fetch notifications for user {user_id}: {e}", exc_info=True)
            raise TechnicalError(message="Database fetch error", error_code="NOTIFICATION_FETCH_ERROR")

    async def create_notification(self, notification_data: NotificationCreate) -> NotificationResponse:
        """
        Creates a new notification with explicit user ownership.
        Fixes P0: Raw ORM leak and P1 missing commit.
        """
        try:
            # Note: notification_data already contains user_id based on schema
            new_notification = Notification(
                user_id=notification_data.user_id,
                type=notification_data.type,
                message=notification_data.message,
                read=notification_data.read,
            )
            # The repository.create method already handles commit/refresh
            created_notif = await self.notification_repo.create(new_notification)

            logger.info(f"Created notification {created_notif.id} for user {notification_data.user_id}")
            return NotificationResponse.model_validate(created_notif)

        except Exception as e:
            logger.error(f"Failed to create notification: {e}", exc_info=True)
            # No need for manual rollback here if repo handles it, but kept for absolute safety in case of non-SQLAlchemy errors
            await self.notification_repo.db.rollback()
            raise TechnicalError(message="Notification creation failed", error_code="NOTIFICATION_CREATION_FAILED")

    async def mark_notification_as_read(self, user_id: UUID, notification_id: UUID) -> NotificationResponse:
        """
        Marks a single notification as read, secured by user_id.
        Fixes P0: Broken security and raw ORM leak.
        """
        try:
            db_notification = await self.notification_repo.get_by_id_secured(user_id, notification_id)

            if not db_notification:
                raise EntityNotFound(message="Notification not found")

            # Correct P0 bug: Pass ID and expected update data format to the generic update method
            # SQLRepository.update(entity_id, data)
            updated_notif = await self.notification_repo.update(db_notification.id, {"read": True})

            return NotificationResponse.model_validate(updated_notif)

        except EntityNotFound:
            raise
        except Exception as e:
            logger.error(f"Failed to mark notification {notification_id} as read: {e}", exc_info=True)
            await self.notification_repo.db.rollback()
            raise TechnicalError(message="Update failed", error_code="NOTIFICATION_UPDATE_FAILED")

    async def mark_all_as_read(self, user_id: UUID, user_confirmation: bool = False) -> int:
        """
        Marks all notifications as read for a specific user.
        Fixes P0: Missing user context.
        """
        if not user_confirmation:
            raise TechnicalError(message="Bulk operation requires confirmation", error_code="MISSING_CONFIRMATION")

        try:
            rows_affected = await self.notification_repo.mark_all_as_read(user_id)
            logger.info(f"User {user_id} marked {rows_affected} notifications as read")
            return rows_affected

        except Exception as e:
            logger.error(f"Bulk read update failed for user {user_id}: {e}", exc_info=True)
            raise TechnicalError(message="Bulk operation failed", error_code="BULK_UPDATE_FAILED")

    async def clear_all_notifications(self, user_id: UUID, user_confirmation: bool = False) -> int:
        """
        Deletes ALL notifications for a user.
        Fixes P0: Missing user context and potentially dangerous global delete.
        """
        if not user_confirmation:
            raise TechnicalError(message="Bulk delete requires confirmation", error_code="MISSING_CONFIRMATION")

        try:
            rows_deleted = await self.notification_repo.clear_all(user_id)
            logger.warning(f"User {user_id} cleared {rows_deleted} notifications")
            return rows_deleted

        except Exception as e:
            logger.error(f"Bulk delete failed for user {user_id}: {e}", exc_info=True)
            raise TechnicalError(message="Bulk deletion failed", error_code="BULK_DELETE_FAILED")

    async def get_unread_count(self, user_id: UUID) -> int:
        """
        Returns count of unread notifications scoped to user.
        """
        try:
            return await self.notification_repo.get_unread_count(user_id)
        except Exception as e:
            logger.error(f"Count failed for user {user_id}: {e}", exc_info=True)
            raise TechnicalError(message="Count failed", error_code="COUNT_ERROR")


async def get_notification_service(db: Annotated[AsyncSession, Depends(get_db)]) -> NotificationService:
    """Dependency for getting NotificationService instance."""
    return NotificationService(NotificationRepository(db))
