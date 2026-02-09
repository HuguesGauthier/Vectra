"""
Tests for Notification model.
"""

from uuid import uuid4

import pytest

from app.models.notification import Notification
from app.schemas.notification import (ALLOWED_NOTIFICATION_TYPES,
                                      MAX_MESSAGE_LENGTH, NotificationCreate,
                                      NotificationResponse)


class TestNotificationModel:
    """Test notification model."""

    def test_valid_notification_creation(self):
        """Valid notification should be created."""
        user_id = uuid4()

        notif = Notification(type="info", message="Test notification", user_id=user_id, read=False)

        assert notif.type == "info"
        assert notif.message == "Test notification"
        assert notif.user_id == user_id
        assert notif.read is False

    def test_notification_types(self):
        """All allowed notification types should work."""
        user_id = uuid4()

        for notif_type in ["info", "success", "warning", "error", "system"]:
            notif = Notification(type=notif_type, message="Test", user_id=user_id)
            assert notif.type == notif_type

    def test_default_read_is_false(self):
        """New notifications should be unread by default."""
        notif = Notification(type="info", message="Test", user_id=uuid4())
        assert notif.read is False

    def test_read_can_be_set_true(self):
        """Notifications can be marked as read."""
        notif = Notification(type="info", message="Test", user_id=uuid4(), read=True)
        assert notif.read is True


class TestNotificationCreate:
    """Test NotificationCreate schema."""

    def test_notification_create_requires_user_id(self):
        """NotificationCreate should require user_id."""
        user_id = uuid4()

        create = NotificationCreate(type="success", message="Task completed", user_id=user_id)

        assert create.user_id == user_id
        assert create.type == "success"
        assert create.message == "Task completed"

    def test_notification_create_defaults_read_false(self):
        """NotificationCreate should default read to False."""
        create = NotificationCreate(type="info", message="Test", user_id=uuid4())
        assert create.read is False


class TestNotificationResponse:
    """Test NotificationResponse schema."""

    def test_response_includes_all_fields(self):
        """NotificationResponse should include all necessary fields."""
        notif_id = uuid4()
        user_id = uuid4()

        response = NotificationResponse(
            id=notif_id, user_id=user_id, type="warning", message="Warning message", read=False
        )

        assert response.id == notif_id
        assert response.user_id == user_id
        assert response.type == "warning"
        assert response.message == "Warning message"
        assert response.read is False
