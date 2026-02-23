import asyncio
import sys
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints.notifications import get_notification_service, get_websocket, router
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.core.exceptions import EntityNotFound, VectraException
from app.core.exceptions import EntityNotFound, VectraException
from app.schemas.notification import NotificationResponse

from tests.utils import get_test_app


app = get_test_app()

app.include_router(router, prefix="/api/v1/notifications")

# Mocks
mock_notif_svc = AsyncMock(spec=NotificationService)
mock_ws_manager = MagicMock()


async def override_get_service():
    return mock_notif_svc


def override_get_user():
    return User(id=uuid4(), email="user@test.com")


def override_get_admin():
    return User(id=uuid4(), email="admin@test.com", is_superuser=True)


app.dependency_overrides[get_notification_service] = override_get_service
app.dependency_overrides[get_current_user] = override_get_user
app.dependency_overrides[get_current_admin] = override_get_admin

# Use raise_server_exceptions=False to test error responses
client = TestClient(app, raise_server_exceptions=False)


class TestNotifications:

    def setup_method(self):
        mock_notif_svc.reset_mock()
        # Ensure async methods are mocked as AsyncMock explicitly if needed or rely on spec
        mock_notif_svc.get_notifications = AsyncMock()
        mock_notif_svc.create_notification = AsyncMock()
        mock_notif_svc.mark_all_as_read = AsyncMock()
        mock_notif_svc.mark_notification_as_read = AsyncMock()
        mock_notif_svc.clear_all_notifications = AsyncMock()

    def test_get_notifications(self):
        """Test listing."""
        mock_notif_svc.get_notifications.return_value = []
        response = client.get("/api/v1/notifications/")
        assert response.status_code == 200
        mock_notif_svc.get_notifications.assert_called_once()

    def test_get_notifications_error(self):
        """Test listing error."""
        mock_notif_svc.get_notifications.side_effect = Exception("error")
        response = client.get("/api/v1/notifications/")
        assert response.status_code == 500
        assert "Failed to fetch notifications" in response.json()["message"]

    def test_create_notification_for_self(self):
        """Test creating a notification for self (default)."""
        data = {"type": "info", "message": "Test Notif", "read": False}

        mock_response = NotificationResponse(
            id=uuid4(), type="info", message=data["message"], read=False, user_id=uuid4(), created_at=None
        )

        mock_notif_svc.create_notification.return_value = mock_response

        response = client.post("/api/v1/notifications/", json=data)
        assert response.status_code == 200
        assert response.json()["message"] == data["message"]
        mock_notif_svc.create_notification.assert_called_once()
        # Verify it used admin's ID (mocked in override_get_admin)
        args, kwargs = mock_notif_svc.create_notification.call_args
        assert args[0].user_id is not None

    def test_create_notification_for_target_user(self):
        """Test creating a notification for a target user (P0 fix)."""
        target_id = uuid4()
        data = {"type": "warning", "message": "Admin Alert", "target_user_id": str(target_id)}

        mock_response = NotificationResponse(
            id=uuid4(), type="warning", message=data["message"], read=False, user_id=target_id, created_at=None
        )

        mock_notif_svc.create_notification.return_value = mock_response

        response = client.post("/api/v1/notifications/", json=data)
        assert response.status_code == 200
        assert response.json()["user_id"] == str(target_id)

        # Verify target_user_id was passed correctly to service
        args, kwargs = mock_notif_svc.create_notification.call_args
        assert str(args[0].user_id) == str(target_id)

    def test_create_notification_error(self):
        """Test creation error."""
        data = {"type": "info", "message": "Test Notif", "read": False, "user_id": str(uuid4())}
        mock_notif_svc.create_notification.side_effect = Exception("error")
        response = client.post("/api/v1/notifications/", json=data)
        assert response.status_code == 500

    def test_mark_notification_read(self):
        """Test marking a single notification as read."""
        notif_id = uuid4()
        mock_response = NotificationResponse(
            id=notif_id, type="info", message="Read me", read=True, user_id=uuid4(), created_at=None
        )

        mock_notif_svc.mark_notification_as_read.return_value = mock_response

        response = client.put(f"/api/v1/notifications/{notif_id}/read")
        assert response.status_code == 200
        assert response.json()["read"] is True

    def test_mark_notification_read_not_found(self):
        """Test mark read not found."""
        notif_id = str(uuid4())
        mock_notif_svc.mark_notification_as_read.return_value = None
        response = client.put(f"/api/v1/notifications/{notif_id}/read")
        assert response.status_code == 404

    def test_mark_notification_read_invalid_uuid(self):
        """Test mark read invalid uuid."""
        response = client.put("/api/v1/notifications/invalid-uuid/read")
        # FastAPI handles UUID validation now, returns 422 for path mismatch
        assert response.status_code == 422

    def test_mark_notification_read_entity_not_found(self):
        """Test mark read entity not found exception."""
        notif_id = str(uuid4())
        mock_notif_svc.mark_notification_as_read.side_effect = EntityNotFound("Not found")
        response = client.put(f"/api/v1/notifications/{notif_id}/read")
        assert response.status_code == 404

    def test_mark_notification_read_error(self):
        """Test mark read error."""
        notif_id = str(uuid4())
        mock_notif_svc.mark_notification_as_read.side_effect = Exception("error")
        response = client.put(f"/api/v1/notifications/{notif_id}/read")
        assert response.status_code == 500

    def test_mark_all_read_passes_confirmation(self):
        """Test bulk read passes confirmation flag."""
        response = client.put("/api/v1/notifications/read")
        assert response.status_code == 200
        assert response.json() == {"message": "All notifications marked as read", "success": True}
        mock_notif_svc.mark_all_as_read.assert_called_with(user_id=ANY, user_confirmation=True)

    def test_mark_all_read_error(self):
        """Test mark all read error."""
        mock_notif_svc.mark_all_as_read.side_effect = Exception("error")
        response = client.put("/api/v1/notifications/read")
        assert response.status_code == 500

    def test_clear_all_notifications(self):
        """Test clear all passes confirmation."""
        response = client.delete("/api/v1/notifications/")
        assert response.status_code == 200
        assert response.json() == {"message": "All notifications cleared", "success": True}
        mock_notif_svc.clear_all_notifications.assert_called_with(user_id=ANY, user_confirmation=True)

    def test_clear_all_notifications_error(self):
        """Test clear all error."""
        mock_notif_svc.clear_all_notifications.side_effect = Exception("error")
        response = client.delete("/api/v1/notifications/")
        assert response.status_code == 500

