import logging
from typing import Annotated, AsyncGenerator, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.websocket import Websocket, get_websocket
from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.notification import NotificationBase, NotificationCreate, NotificationResponse
from app.services.notification_service import NotificationService, get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Request Schema for this endpoint
class NotificationCreateRequest(NotificationBase):
    """
    Schema for creating a notification through the API.

    Inherits from NotificationBase.
    """

    pass


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

    Args:
        notification_in: The notification data.
        service: The notification service instance.
        current_user: The currently authenticated admin user.

    Returns:
        NotificationResponse: The created notification.

    Raises:
        TechnicalError: If there's an error creating the notification.
    """
    try:
        # P0: Inject user_id from token, don't trust client
        notification = NotificationCreate(**notification_in.model_dump(), user_id=current_user.id)
        return await service.create_notification(notification)
    except Exception as e:
        logger.error(f"❌ FAIL | create_notification | Error: {str(e)}", exc_info=True)
        if isinstance(e, (FunctionalError, TechnicalError)):
            raise
        raise TechnicalError(f"Failed to create notification: {e}")


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationResponse:
    """
    Mark a specific notification as read.

    Args:
        notification_id: The UUID of the notification to mark as read.
        service: The notification service instance.
        current_user: The currently authenticated user.

    Returns:
        NotificationResponse: The updated notification.

    Raises:
        FunctionalError: If the notification_id is not a valid UUID.
        EntityNotFound: If the notification is not found.
        TechnicalError: If there's an error updating the notification.
    """
    try:
        uuid_id = UUID(notification_id)
        notification = await service.mark_notification_as_read(user_id=current_user.id, notification_id=uuid_id)
        if not notification:
            raise EntityNotFound("Notification not found")
        return notification
    except ValueError:
        raise FunctionalError("Invalid UUID format", error_code="invalid_uuid", status_code=400)
    except EntityNotFound:
        raise
    except Exception as e:
        logger.error(
            f"❌ FAIL | mark_notification_read | ID: {notification_id} | Error: {str(e)}",
            exc_info=True,
        )
        raise TechnicalError(f"Failed to mark notification as read: {e}")


@router.put("/read", response_model=Dict[str, str])
async def mark_all_notifications_read(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, str]:
    """
    Mark all notifications as read for the current user.

    Args:
        service: The notification service instance.
        current_user: The currently authenticated user.

    Returns:
        Dict[str, str]: A dictionary with a success message.

    Raises:
        TechnicalError: If there's an error updating notifications.
    """
    try:
        # Pass user context and confirmation
        await service.mark_all_as_read(user_id=current_user.id, user_confirmation=True)
        return {"message": "All notifications marked as read"}
    except Exception as e:
        logger.error(f"❌ FAIL | mark_all_notifications_read | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to mark all notifications as read: {e}")


@router.delete("/", response_model=Dict[str, str])
async def clear_all_notifications(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, str]:
    """
    Clear all notifications (Admin only).

    Args:
        service: The notification service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, str]: A dictionary with a success message.

    Raises:
        TechnicalError: If there's an error clearing notifications.
    """
    try:
        # Pass user context and confirmation
        await service.clear_all_notifications(user_id=current_user.id, user_confirmation=True)
        return {"message": "All notifications cleared"}
    except Exception as e:
        logger.error(f"❌ FAIL | clear_all_notifications | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to clear all notifications: {e}")
