import logging
from typing import Annotated, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.websocket import Websocket, get_websocket
from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.notification import NotificationBase, NotificationCreate, NotificationResponse
from app.services.notification_service import NotificationService, get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class NotificationCreateRequest(NotificationBase):
    """
    Schema for creating a notification through the API.
    """

    target_user_id: Optional[UUID] = Field(
        default=None, description="The UUID of the user to notify (defaults to self if not provided)"
    )


@router.get("/stream")
async def stream_notifications(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    manager: Websocket = Depends(get_websocket),
) -> StreamingResponse:
    """
    SSE Stream for real-time notifications.

    Provides a Server-Sent Events (SSE) stream that delivers real-time notifications
    to the authenticated user.

    Args:
        request: The FastAPI request object.
        current_user: The currently authenticated user.
        manager: The websocket manager instance.

    Returns:
        StreamingResponse: A response delivering SSE events.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """
        Generates SSE events from the connection manager.

        Yields:
            str: Formatted SSE data strings.
        """
        # "The Architect Way": Use the safe generator that guarantees cleanup and capped queues
        async for message in manager.stream_events():
            if await request.is_disconnected():
                break
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[NotificationResponse]:
    """
    List all notifications for the current user.

    Args:
        service: The notification service instance.
        current_user: The currently authenticated user.

    Returns:
        List[NotificationResponse]: A list of notifications for the user.

    Raises:
        TechnicalError: If there's an error fetching notifications.
    """
    try:
        return await service.get_notifications(user_id=current_user.id)
    except Exception as e:
        logger.error(f"❌ FAIL | get_notifications | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to fetch notifications: {e}")


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_in: NotificationCreateRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> NotificationResponse:
    """
    Create a notification (Admin only).

    If target_user_id is provided, the notification will be created for that user.
    Otherwise, it will be created for the admin currently authenticated.
    """
    try:
        # P0: Allow admin to notify others
        target_id = notification_in.target_user_id or current_user.id

        notification = NotificationCreate(**notification_in.model_dump(exclude={"target_user_id"}), user_id=target_id)
        return await service.create_notification(notification)
    except Exception as e:
        logger.error(f"❌ FAIL | create_notification | Error: {str(e)}", exc_info=True)
        if isinstance(e, (FunctionalError, TechnicalError)):
            raise
        raise TechnicalError(f"Failed to create notification: {e}")


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationResponse:
    """
    Mark a specific notification as read.
    """
    try:
        notification = await service.mark_notification_as_read(user_id=current_user.id, notification_id=notification_id)
        if not notification:
            # Should technically be handled by service raising EntityNotFound
            raise EntityNotFound("Notification not found")
        return notification
    except EntityNotFound:
        raise
    except Exception as e:
        logger.error(
            f"❌ FAIL | mark_notification_read | ID: {notification_id} | Error: {str(e)}",
            exc_info=True,
        )
        raise TechnicalError(f"Failed to mark notification as read: {e}")


@router.put("/read", response_model=MessageResponse)
async def mark_all_notifications_read(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """
    Mark all notifications as read for the current user.
    """
    try:
        # Pass user context and confirmation
        await service.mark_all_as_read(user_id=current_user.id, user_confirmation=True)
        return MessageResponse(message="All notifications marked as read")
    except Exception as e:
        logger.error(f"❌ FAIL | mark_all_notifications_read | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to mark all notifications as read: {e}")


@router.delete("/", response_model=MessageResponse)
async def clear_all_notifications(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> MessageResponse:
    """
    Clear all notifications (Admin only).
    """
    try:
        # Pass user context and confirmation
        await service.clear_all_notifications(user_id=current_user.id, user_confirmation=True)
        return MessageResponse(message="All notifications cleared")
    except Exception as e:
        logger.error(f"❌ FAIL | clear_all_notifications | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to clear all notifications: {e}")
