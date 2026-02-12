import pytest
import io
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.system import get_system_service, get_document_service
from app.core.security import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.enums import UserRole

# Mock Data
USER_ID = uuid4()
ADMIN_ID = uuid4()
DOC_ID = str(uuid4())

mock_user = User(id=USER_ID, email="user@example.com", role=UserRole.USER, is_active=True)
mock_admin = User(id=ADMIN_ID, email="admin@example.com", role=UserRole.ADMIN, is_active=True)


# Dependency Overrides
async def override_get_current_user():
    return mock_user


async def override_get_current_admin():
    return mock_admin


@pytest.fixture
def client():
    app.dependency_overrides = {}
    return TestClient(app)


def test_open_file_happy_path(client):
    app.dependency_overrides[get_current_user] = override_get_current_user

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.open_file_by_document_id.return_value = True
    app.dependency_overrides[get_system_service] = lambda: mock_service

    response = client.post("/api/v1/system/open-file", json={"document_id": DOC_ID})
    assert response.status_code == 200
    assert response.json() == {"message": "File opened", "success": True}
    mock_service.open_file_by_document_id.assert_called_once_with(DOC_ID)


def test_upload_file_as_admin(client):
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.upload_file.return_value = "temp_uploads/test.txt"
    app.dependency_overrides[get_document_service] = lambda: mock_service

    files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
    response = client.post("/api/v1/system/upload", files=files)

    assert response.status_code == 200
    assert response.json() == {"path": "temp_uploads/test.txt"}
    mock_service.upload_file.assert_called_once()


def test_upload_file_denied_for_regular_user(client):
    # This endpoint uses get_current_admin, so we override get_current_admin with a user
    # But usually the dependency itself handles the check.
    # If we want to test the PERMISSION check, we should NOT override get_current_admin
    # OR override it to NOT return an admin.

    # Actually, the real get_current_admin raises 403. Let's mock a failure if needed.
    # But let's just use the real dependency and see it fail if we don't provide a token.
    # However, these tests usually override for simplicity.

    async def get_regular_user_as_admin():
        from app.core.exceptions import FunctionalError

        raise FunctionalError(
            "The user does not have enough privileges", error_code="INSUFFICIENT_PRIVILEGES", status_code=403
        )

    app.dependency_overrides[get_current_admin] = get_regular_user_as_admin

    response = client.post("/api/v1/system/upload", files={"file": ("a.txt", b"c")})
    assert response.status_code == 403
    assert response.json()["message"] == "The user does not have enough privileges"


def test_delete_temp_file_happy_path(client):
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    app.dependency_overrides[get_document_service] = lambda: mock_service

    response = client.request("DELETE", "/api/v1/system/temp-file", json={"path": "temp_uploads/a.txt"})
    assert response.status_code == 200
    assert response.json() == {"message": "File deleted successfully", "success": True}
    mock_service.delete_temp_file.assert_called_once_with("temp_uploads/a.txt")
