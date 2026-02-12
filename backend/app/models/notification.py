"""
Notification Database Model.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum, Index, func
from sqlmodel import Field, SQLModel

from app.models.enums import NotificationType
from app.schemas.notification import NotificationBase


class Notification(NotificationBase, table=True):
    """
    Database model for Notifications.
    Inherits schema/validation from NotificationBase in schemas/.
    """

    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)

    created_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True)
    )

    # Explicitly map the Enum column for SQLAlchemy
    type: NotificationType = Field(
        sa_column=Column(
            Enum(NotificationType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False
        )
    )

    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "read", "created_at"),
        Index("ix_notifications_user_type", "user_id", "type"),
    )
