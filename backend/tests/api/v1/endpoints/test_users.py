import pytest
import io
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.users import get_current_user, get_current_admin, get_user_service
from app.models.user import User
from app.schemas.enums import UserRole
from app.schemas.user import UserRead

# Mock Data
USER_ID = uuid4()
ADMIN_ID = uuid4()
OTHER_USER_ID = uuid4()

mock_user = User(
    id=USER_ID, email="user@example.com", role=UserRole.USER, is_active=True, first_name="Regular", last_name="User"
)

mock_admin = User(
    id=ADMIN_ID, email="admin@example.com", role=UserRole.ADMIN, is_active=True, first_name="Admin", last_name="User"
)


# Dependency Overrides
async def override_get_current_user():
    return mock_user


async def override_get_current_admin():
    return mock_admin


@pytest.fixture
def client():
    # Reset overrides for each test to be safe
    app.dependency_overrides = {}
    return TestClient(app)


def test_read_user_me(client):
    app.dependency_overrides[get_current_user] = override_get_current_user
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email
    assert data["id"] == str(USER_ID)


def test_read_users_as_admin(client):
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    # We also need to mock the service to avoid DB calls
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_multi.return_value = [mock_user, mock_admin]
    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["email"] == mock_user.email


def test_upload_avatar_own_profile(client):
    app.dependency_overrides[get_current_user] = override_get_current_user

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.upload_avatar.return_value = mock_user
    app.dependency_overrides[get_user_service] = lambda: mock_service

    avatar_content = b"fake image content"
    files = {"file": ("avatar.png", io.BytesIO(avatar_content), "image/png")}

    response = client.post(f"/api/v1/users/{USER_ID}/avatar", files=files)
    assert response.status_code == 200
    mock_service.upload_avatar.assert_called_once()


def test_upload_avatar_other_profile_denied(client):
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Attempting to upload avatar for ANOTHER user when I'm just a regular user
    response = client.post(f"/api/v1/users/{OTHER_USER_ID}/avatar", files={"file": ("a.png", b"c", "image/png")})
    assert response.status_code == 403
    assert response.json()["message"] == "Not authorized"


def test_upload_avatar_as_admin_for_other(client):
    # Mock current_user as ADMIN
    app.dependency_overrides[get_current_user] = override_get_current_admin

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.upload_avatar.return_value = mock_user
    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = client.post(f"/api/v1/users/{USER_ID}/avatar", files={"file": ("a.png", b"c", "image/png")})
    assert response.status_code == 200
    mock_service.upload_avatar.assert_called_once()


def test_get_avatar_not_found(client):
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_avatar_path.return_value = None
    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = client.get(f"/api/v1/users/{USER_ID}/avatar")
    assert response.status_code == 404
    assert response.json()["message"] == "Avatar not found"


def test_delete_user_as_admin(client):
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.delete.return_value = mock_user
    app.dependency_overrides[get_user_service] = lambda: mock_service

    response = client.delete(f"/api/v1/users/{USER_ID}")
    assert response.status_code == 200
    mock_service.delete.assert_called_once_with(USER_ID)
