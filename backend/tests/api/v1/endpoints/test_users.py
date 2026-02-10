from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.users import router
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.services.user_service import UserService, get_user_service

# Mock Service Instance
mock_user_svc = AsyncMock(spec=UserService)

# Setup App
app = FastAPI()
app.include_router(router, prefix="/api/v1/users")


async def override_get_user_service():
    return mock_user_svc


def override_get_admin():
    return User(id=uuid4(), email="admin@test.com", is_superuser=True, role="admin", is_active=True)


def override_get_user():
    return User(id=uuid4(), email="user@test.com", is_superuser=False, role="user", is_active=True)


app.dependency_overrides[get_user_service] = override_get_user_service
app.dependency_overrides[get_current_admin] = override_get_admin
app.dependency_overrides[get_current_user] = override_get_user

client = TestClient(app)


class TestUsers:
    def setup_method(self):
        mock_user_svc.reset_mock()
        app.dependency_overrides[get_current_admin] = override_get_admin

    def test_read_users_admin(self):
        """Test reading users allows admin."""
        mock_user_svc.get_multi.return_value = []
        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert response.json() == []
        mock_user_svc.get_multi.assert_called_once()

    def test_read_users_unauthorized(self):
        """Test reading users rejects non-admin."""

        # Override to throw exception (simulating auth failure in Depends)
        def override_fail():
            raise Exception("Not Admin")

        # We override the direct dependency used by the endpoint
        app.dependency_overrides[get_current_admin] = override_fail

        try:
            client.get("/api/v1/users/")
        except Exception as e:
            assert "Not Admin" in str(e)

    def test_create_user(self):
        """Test create user delegates to service."""
        new_user = {"email": "new@test.com", "password": "password", "role": "user"}
        mock_user_svc.create.return_value = User(id=uuid4(), email=new_user["email"], role="user")

        response = client.post("/api/v1/users/", json=new_user)
        assert response.status_code == 200
        assert response.json()["email"] == new_user["email"]
        mock_user_svc.create.assert_called_once()

    def test_read_me(self):
        """Test read /me returns current user."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == "user@test.com"
