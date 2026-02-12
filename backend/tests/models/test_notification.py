"""
Tests for Notification model.
"""

from uuid import uuid4

import pytest

from app.models.notification import Notification
from app.models.enums import NotificationType


class TestNotificationModel:
    """Test notification model."""

    def test_valid_notification_creation(self):
        """Valid notification should be created."""
        user_id = uuid4()

        notif = Notification(type=NotificationType.INFO, message="Test notification", user_id=user_id, read=False)

        assert notif.type == NotificationType.INFO
        assert notif.message == "Test notification"
        assert notif.user_id == user_id
        assert notif.read is False

    def test_notification_types(self):
        """All allowed notification types should work."""
        user_id = uuid4()

        for notif_type in NotificationType:
            notif = Notification(type=notif_type, message="Test", user_id=user_id)
            assert notif.type == notif_type

    def test_default_read_is_false(self):
        """New notifications should be unread by default."""
        notif = Notification(type=NotificationType.INFO, message="Test", user_id=uuid4())
        assert notif.read is False

    def test_read_can_be_set_true(self):
        """Notifications can be marked as read."""
        notif = Notification(type=NotificationType.INFO, message="Test", user_id=uuid4(), read=True)
        assert notif.read is True
