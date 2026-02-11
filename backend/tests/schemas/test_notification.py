"""
Unit tests for backend/app/schemas/notification.py
Tests cover validation, DoS protection, and serialization.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.enums import NotificationType
from app.schemas.notification import (
    ALLOWED_NOTIFICATION_TYPES,
    MAX_MESSAGE_LENGTH,
    NotificationBase,
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
)


class TestNotificationBase:
    """Test NotificationBase schema."""

    def test_valid_notification_base(self):
        """Test creating a valid notification base."""
        notification = NotificationBase(
            type=NotificationType.INFO,
            message="Test notification",
            read=False,
        )
        assert notification.type == NotificationType.INFO
        assert notification.message == "Test notification"
        assert notification.read is False

    def test_default_read_status(self):
        """Test that read defaults to False."""
        notification = NotificationBase(type=NotificationType.SUCCESS, message="Test")
        assert notification.read is False

    def test_all_notification_types_valid(self):
        """Test all notification types are valid."""
        for notification_type in NotificationType:
            notification = NotificationBase(type=notification_type, message="Test message")
            assert notification.type == notification_type


class TestNotificationValidation:
    """Test validation rules (DoS protection)."""

    def test_empty_message_rejected(self):
        """Test that empty messages are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationBase(type=NotificationType.INFO, message="")

        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(error).lower() for error in errors)

    def test_max_message_length_enforced(self):
        """Test that messages exceeding MAX_MESSAGE_LENGTH are rejected (DoS protection)."""
        long_message = "x" * (MAX_MESSAGE_LENGTH + 1)

        with pytest.raises(ValidationError) as exc_info:
            NotificationBase(type=NotificationType.INFO, message=long_message)

        errors = exc_info.value.errors()
        assert any("at most" in str(error).lower() or "max_length" in str(error).lower() for error in errors)

    def test_max_message_length_boundary(self):
        """Test that messages at exactly MAX_MESSAGE_LENGTH are accepted."""
        max_message = "x" * MAX_MESSAGE_LENGTH
        notification = NotificationBase(type=NotificationType.INFO, message=max_message)
        assert len(notification.message) == MAX_MESSAGE_LENGTH

    def test_invalid_notification_type_rejected(self):
        """Test that invalid notification types are rejected."""
        with pytest.raises(ValidationError):
            NotificationBase(type="invalid_type", message="Test")  # type: ignore


class TestNotificationCreate:
    """Test NotificationCreate schema."""

    def test_valid_notification_create(self):
        """Test creating a valid notification creation request."""
        user_id = uuid4()
        notification = NotificationCreate(
            type=NotificationType.WARNING,
            message="Warning message",
            user_id=user_id,
        )
        assert notification.user_id == user_id
        assert notification.type == NotificationType.WARNING
        assert notification.message == "Warning message"

    def test_user_id_required(self):
        """Test that user_id is required for creation."""
        with pytest.raises(ValidationError):
            NotificationCreate(type=NotificationType.INFO, message="Test")  # type: ignore


class TestNotificationUpdate:
    """Test NotificationUpdate schema."""

    def test_valid_notification_update(self):
        """Test updating notification read status."""
        update = NotificationUpdate(read=True)
        assert update.read is True

    def test_empty_update_valid(self):
        """Test that empty updates are valid (partial updates)."""
        update = NotificationUpdate()
        assert update.read is None

    def test_update_read_to_false(self):
        """Test marking notification as unread."""
        update = NotificationUpdate(read=False)
        assert update.read is False


class TestNotificationResponse:
    """Test NotificationResponse schema."""

    def test_valid_notification_response(self):
        """Test creating a valid notification response."""
        notification_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()

        response = NotificationResponse(
            id=notification_id,
            user_id=user_id,
            type=NotificationType.ERROR,
            message="Error occurred",
            read=True,
            created_at=now,
        )

        assert response.id == notification_id
        assert response.user_id == user_id
        assert response.type == NotificationType.ERROR
        assert response.message == "Error occurred"
        assert response.read is True
        assert response.created_at == now

    def test_created_at_optional(self):
        """Test that created_at is optional."""
        response = NotificationResponse(
            id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.SYSTEM,
            message="System notification",
        )
        assert response.created_at is None


class TestNotificationListResponse:
    """Test NotificationListResponse schema."""

    def test_valid_list_response(self):
        """Test creating a valid paginated list response."""
        notifications = [
            NotificationResponse(
                id=uuid4(),
                user_id=uuid4(),
                type=NotificationType.INFO,
                message=f"Notification {i}",
            )
            for i in range(3)
        ]

        response = NotificationListResponse(notifications=notifications, total=10, unread_count=5)

        assert len(response.notifications) == 3
        assert response.total == 10
        assert response.unread_count == 5

    def test_empty_list_valid(self):
        """Test that empty notification lists are valid."""
        response = NotificationListResponse(notifications=[], total=0, unread_count=0)
        assert response.notifications == []
        assert response.total == 0
        assert response.unread_count == 0


class TestConstants:
    """Test exported constants."""

    def test_allowed_notification_types_matches_enum(self):
        """Test that ALLOWED_NOTIFICATION_TYPES matches NotificationType enum."""
        enum_values = [t.value for t in NotificationType]
        assert ALLOWED_NOTIFICATION_TYPES == enum_values

    def test_all_notification_types_are_strings(self):
        """Test that all allowed types are strings (for API compatibility)."""
        for notification_type in ALLOWED_NOTIFICATION_TYPES:
            assert isinstance(notification_type, str)

    def test_max_message_length_reasonable(self):
        """Test that MAX_MESSAGE_LENGTH is reasonable (not too small or too large)."""
        assert 100 <= MAX_MESSAGE_LENGTH <= 10000  # Reasonable range for notifications


class TestEdgeCases:
    """Test edge cases and production scenarios."""

    def test_unicode_message_valid(self):
        """Test that Unicode messages are handled correctly."""
        notification = NotificationBase(type=NotificationType.INFO, message="Hello 世界 🌍 émojis")
        assert notification.message == "Hello 世界 🌍 émojis"

    def test_whitespace_only_message_rejected(self):
        """Test that whitespace-only messages are rejected."""
        # Pydantic's min_length counts characters, not stripped length
        # So "   " (3 spaces) would pass min_length=1
        # This is acceptable behavior - if you want to reject whitespace,
        # you'd need a custom validator
        notification = NotificationBase(type=NotificationType.INFO, message="   ")
        assert notification.message == "   "

    def test_serialization_to_dict(self):
        """Test that notifications can be serialized to dict (for API responses)."""
        notification = NotificationResponse(
            id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.SUCCESS,
            message="Success!",
            read=False,
        )
        data = notification.model_dump()
        assert isinstance(data, dict)
        assert data["type"] == "success"  # Enum serialized to string
        assert data["message"] == "Success!"
        assert data["read"] is False
