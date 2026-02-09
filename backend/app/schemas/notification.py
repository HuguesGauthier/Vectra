"""
Notification Schemas - Pydantic definitions for API request/response.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field
from sqlmodel import SQLModel

from app.schemas.enums import NotificationType

# Constants
MAX_TYPE_LENGTH = 50
MAX_MESSAGE_LENGTH = 1000
ALLOWED_NOTIFICATION_TYPES = [t.value for t in NotificationType]


class NotificationBase(SQLModel):
    """
    Base properties for Notification.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # We use the Enum for validation, but store as string in DB usually
    # (or Enum column, but SQLModel+Enum can be tricky with migrations sometimes,
    # though here we are defining Schema).
    # Since we want strict API validation, we use the Enum type here.
    type: NotificationType = Field(description="Notification severity/category")

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH, description="Notification content")
    read: bool = Field(default=False, description="Read status")


class NotificationCreate(NotificationBase):
    """Schema for Creation."""

    user_id: UUID


class NotificationUpdate(SQLModel):
    """Schema for Partial Updates."""

    read: Optional[bool] = None


class NotificationResponse(NotificationBase):
    """Schema for Response."""

    id: UUID
    user_id: UUID
    created_at: Optional[datetime] = None


class NotificationListResponse(SQLModel):
    """Paginated list response."""

    notifications: List[NotificationResponse]
    total: int
    unread_count: int
