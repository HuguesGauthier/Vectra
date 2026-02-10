import pytest
from httpx import AsyncClient
from typing import Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone # Import datetime and timezone

from fastapi import status
from fastapi.testclient import TestClient # Import TestClient
from fastapi.responses import FileResponse # Import FileResponse for proper mocking

from app.schemas.assistant import AssistantResponse, AssistantCreate, AssistantUpdate
from app.models.user import User
from app.main import app # Import the main FastAPI app


# Mock dependencies
@pytest.fixture
def mock_assistant_service():
    """Provides a mock AssistantService instance."""
    return AsyncMock()

@pytest.fixture
def mock_current_admin():
    """Provides a mock admin user for authenticated endpoints."""
    return User(id=uuid4(), email="admin@example.com", is_admin=True)

@pytest.fixture
def mock_current_user_optional():
    """Provides a mock regular user for authenticated endpoints."""
    return User(id=uuid4(), email="user@example.com", is_admin=False)


@pytest.fixture(scope="module")
def client():
    """Provides a synchronous test client for the FastAPI application."""
    with TestClient(app=app) as client_instance:
        yield client_instance


@pytest.mark.asyncio
async def test_root_endpoint(client: TestClient):
    """Test the root endpoint to ensure basic client functionality and app routing."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_get_assistants_public_access(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving assistants with public access (no user authenticated)."""
    # Add created_at and updated_at to AssistantResponse instances
    now = datetime.now(timezone.utc)
    assistant_1 = AssistantResponse(id=uuid4(), name="Public Assistant 1", user_authentication=False, private_assistant=False, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    assistant_2 = AssistantResponse(id=uuid4(), name="Private Assistant 1", user_authentication=False, private_assistant=True, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistants.return_value = [assistant_1, assistant_2]

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None):
        response = client.get("/api/v1/assistants/")

    if response.status_code != status.HTTP_200_OK:
        print(f"DEBUG: Response Status Code: {response.status_code}")
        print(f"DEBUG: Response Headers: {response.headers}")
        print(f"DEBUG: Response Content: {response.text}")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Public Assistant 1"
    mock_assistant_service.get_assistants.assert_called_once_with(exclude_private=True)


@pytest.mark.asyncio
async def test_get_assistants_authenticated_user(client: TestClient, mock_assistant_service: AsyncMock, mock_current_user_optional: User):
    """Test retrieving assistants with an authenticated user."""
    now = datetime.now(timezone.utc)
    assistant_1 = AssistantResponse(id=uuid4(), name="Public Assistant 1", user_authentication=False, private_assistant=False, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    assistant_2 = AssistantResponse(id=uuid4(), name="Private Assistant 1", user_authentication=False, private_assistant=True, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistants.return_value = [assistant_1, assistant_2]

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=mock_current_user_optional):
        response = client.get("/api/v1/assistants/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Public Assistant 1"
    assert response.json()[1]["name"] == "Private Assistant 1"
    mock_assistant_service.get_assistants.assert_called_once_with(exclude_private=False)


@pytest.mark.asyncio
async def test_get_assistant_success_public(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving a single public assistant by ID."""
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    assistant = AssistantResponse(id=assistant_id, name="Test Assistant", user_authentication=False, private_assistant=False, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistant.return_value = assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None):
        response = client.get(f"/api/v1/assistants/{assistant_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Test Assistant"
    mock_assistant_service.get_assistant.assert_called_once_with(assistant_id)


@pytest.mark.asyncio
async def test_get_assistant_not_found(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving a non-existent assistant."""
    assistant_id = uuid4()
    mock_assistant_service.get_assistant.return_value = None

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None):
        response = client.get(f"/api/v1/assistants/{assistant_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Assistant not found" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_assistant_authentication_required_unauthorized(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving an assistant that requires authentication without a logged-in user."""
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    assistant = AssistantResponse(id=assistant_id, name="Private Test Assistant", user_authentication=True, private_assistant=True, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistant.return_value = assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None):
        response = client.get(f"/api/v1/assistants/{assistant_id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication required for this assistant" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_assistant_authentication_required_authorized(client: TestClient, mock_assistant_service: AsyncMock, mock_current_user_optional: User):
    """
    Test retrieving an assistant that requires authentication with a logged-in user.
    This should succeed even if the user is not an admin.
    """
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    assistant = AssistantResponse(id=assistant_id, name="Private Test Assistant", user_authentication=True, private_assistant=True, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistant.return_value = assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=mock_current_user_optional):
        response = client.get(f"/api/v1/assistants/{assistant_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Private Test Assistant"
    mock_assistant_service.get_assistant.assert_called_once_with(assistant_id)


@pytest.mark.asyncio
async def test_create_assistant_success(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test creating an assistant as an admin."""
    create_data = AssistantCreate(name="New Assistant", description="A new assistant.", user_authentication=False, private_assistant=False, llm_id=uuid4(), prompt_id=uuid4())
    now = datetime.now(timezone.utc)
    created_assistant = AssistantResponse(id=uuid4(), **create_data.model_dump(), avatar_url=None, created_at=now, updated_at=now)
    mock_assistant_service.create_assistant.return_value = created_assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.post("/api/v1/assistants/", json=create_data.model_dump())

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "New Assistant"
    mock_assistant_service.create_assistant.assert_called_once()


@pytest.mark.asyncio
async def test_create_assistant_unauthorized(client: TestClient):
    """Test creating an assistant without admin privileges."""
    create_data = AssistantCreate(name="New Assistant", description="A new assistant.", user_authentication=False, private_assistant=False, llm_id=uuid4(), prompt_id=uuid4())

    with patch("app.api.v1.endpoints.assistants.get_current_admin", side_effect=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")):
        response = client.post("/api/v1/assistants/", json=create_data.model_dump())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["message"] == "Unauthorized"


@pytest.mark.asyncio
async def test_update_assistant_success(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test updating an existing assistant as an admin."""
    assistant_id = uuid4()
    update_data = AssistantUpdate(name="Updated Assistant Name")
    now = datetime.now(timezone.utc)
    updated_assistant = AssistantResponse(id=assistant_id, name="Updated Assistant Name", user_authentication=False, private_assistant=False, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.update_assistant.return_value = updated_assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.put(f"/api/v1/assistants/{assistant_id}", json=update_data.model_dump())

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated Assistant Name"
    mock_assistant_service.update_assistant.assert_called_once_with(assistant_id, update_data)


@pytest.mark.asyncio
async def test_update_assistant_not_found(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test updating a non-existent assistant."""
    assistant_id = uuid4()
    update_data = AssistantUpdate(name="Updated Assistant Name")
    mock_assistant_service.update_assistant.return_value = None

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.put(f"/api/v1/assistants/{assistant_id}", json=update_data.model_dump())

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Assistant not found" in response.json()["message"]


@pytest.mark.asyncio
async def test_delete_assistant_success(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test deleting an existing assistant as an admin."""
    assistant_id = uuid4()
    mock_assistant_service.delete_assistant.return_value = True

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.delete(f"/api/v1/assistants/{assistant_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_assistant_service.delete_assistant.assert_called_once_with(assistant_id)


@pytest.mark.asyncio
async def test_delete_assistant_not_found(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test deleting a non-existent assistant."""
    assistant_id = uuid4()
    mock_assistant_service.delete_assistant.return_value = False

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.delete(f"/api/v1/assistants/{assistant_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Assistant not found" in response.json()["message"]


@pytest.mark.asyncio
async def test_upload_assistant_avatar_success(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test uploading an avatar for an assistant as an admin."""
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    updated_assistant = AssistantResponse(id=assistant_id, name="Test Assistant", user_authentication=False, private_assistant=False, avatar_url="http://example.com/avatar.png", llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.upload_avatar.return_value = updated_assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        # Create a dummy file for upload
        files = {"file": ("test.png", b"file_content", "image/png")}
        response = client.post(f"/api/v1/assistants/{assistant_id}/avatar", files=files)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["avatar_url"] == "http://example.com/avatar.png"
    mock_assistant_service.upload_avatar.assert_called_once()


@pytest.mark.asyncio
async def test_delete_assistant_avatar_success(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test deleting an avatar for an assistant as an admin."""
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    updated_assistant = AssistantResponse(id=assistant_id, name="Test Assistant", user_authentication=False, private_assistant=False, avatar_url=None, llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.remove_avatar.return_value = updated_assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.delete(f"/api/v1/assistants/{assistant_id}/avatar")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["avatar_url"] is None
    mock_assistant_service.remove_avatar.assert_called_once_with(assistant_id)


@pytest.mark.asyncio
async def test_get_assistant_avatar_success_public(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving a public assistant's avatar."""
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    assistant = AssistantResponse(id=assistant_id, name="Test Assistant", user_authentication=False, private_assistant=False, avatar_url="path/to/avatar.png", llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistant.return_value = assistant
    mock_assistant_service.get_avatar_path.return_value = "d:/temp/avatar.png"

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None), \
         patch("app.api.v1.endpoints.assistants.FileResponse") as mock_file_response_cls:
        response = client.get(f"/api/v1/assistants/{assistant_id}/avatar")

    # Assert that FileResponse was called with the correct path
    mock_file_response_cls.assert_called_once_with("d:/temp/avatar.png")
    # Also, we can check the status code of the actual response object if needed
    # However, since FileResponse is mocked, the 'response' here will be the mock object itself
    # For now, asserting the call is sufficient.
    assert isinstance(response, FileResponse)


@pytest.mark.asyncio
async def test_get_assistant_avatar_not_found(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving a non-existent assistant's avatar."""
    assistant_id = uuid4()
    mock_assistant_service.get_assistant.return_value = None

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None):
        response = client.get(f"/api/v1/assistants/{assistant_id}/avatar")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Avatar not found" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_assistant_avatar_private_unauthorized(client: TestClient, mock_assistant_service: AsyncMock):
    """Test retrieving a private assistant's avatar without authorization (guest)."""
    assistant_id = uuid4()
    now = datetime.now(timezone.utc)
    assistant = AssistantResponse(id=assistant_id, name="Private Assistant", user_authentication=True, private_assistant=True, avatar_url="path/to/avatar.png", llm_id=uuid4(), prompt_id=uuid4(), created_at=now, updated_at=now)
    mock_assistant_service.get_assistant.return_value = assistant

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_user_optional", return_value=None):
        response = client.get(f"/api/v1/assistants/{assistant_id}/avatar")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Avatar not found" in response.json()["message"] # Obfuscated as not found


@pytest.mark.asyncio
async def test_clear_assistant_cache_success(client: TestClient, mock_assistant_service: AsyncMock, mock_current_admin: User):
    """Test clearing an assistant's cache as an admin."""
    assistant_id = uuid4()
    mock_assistant_service.clear_cache.return_value = 5

    with patch("app.api.v1.endpoints.assistants.get_assistant_service", return_value=mock_assistant_service), \
         patch("app.api.v1.endpoints.assistants.get_current_admin", return_value=mock_current_admin):
        response = client.delete(f"/api/v1/assistants/{assistant_id}/cache")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"deleted_count": 5}
    mock_assistant_service.clear_cache.assert_called_once_with(assistant_id)
