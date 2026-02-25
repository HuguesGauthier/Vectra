"""
Tests for Notification Schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.notification import NotificationCreate, NotificationType


def test_notification_create_valid():
    n = NotificationCreate(user_id=uuid4(), type=NotificationType.INFO, message="Test msg")
    assert n.type == NotificationType.INFO
    assert n.read is False


def test_notification_invalid_type():
    with pytest.raises(ValidationError) as exc:
        NotificationCreate(user_id=uuid4(), type="invalid_type", message="msg")
    assert "Input should be 'info', 'success', 'warning', 'error' or 'system'" in str(exc.value)


def test_notification_message_length():
    with pytest.raises(ValidationError) as exc:
        NotificationCreate(user_id=uuid4(), type=NotificationType.ERROR, message="a" * 1001)
    assert "at most 1000 characters" in str(exc.value)
