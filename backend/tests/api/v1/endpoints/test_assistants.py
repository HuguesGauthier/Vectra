import io
import logging
from datetime import datetime
from typing import Optional, Union, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

from app.api.v1.endpoints.assistants import router
from app.core.security import get_current_admin, get_current_user_optional
from app.models.user import User
from app.schemas.assistant import AssistantResponse, AIModel
from app.services.assistant_service import AssistantService, get_assistant_service
from app.core.exceptions import EntityNotFound, TechnicalError, FunctionalError, VectraException
from app.main import global_exception_handler

app = FastAPI()
app.include_router(router, prefix="/api/v1/assistants")

# Use real global exception handler
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(VectraException, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)

# Setup Mocks
mock_asst_svc = AsyncMock(spec=AssistantService)


async def override_get_service():
    return mock_asst_svc


def override_get_admin():
    return User(id=uuid4(), email="admin@test.com", is_superuser=True)


def override_user_optional() -> Optional[User]:
    return None


app.dependency_overrides[get_assistant_service] = override_get_service
app.dependency_overrides[get_current_admin] = override_get_admin
app.dependency_overrides[get_current_user_optional] = override_user_optional

client = TestClient(app)


class TestAssistants:

    def setup_method(self):
        mock_asst_svc.reset_mock(return_value=True, side_effect=True)
        mock_asst_svc.get_assistants.side_effect = None
        mock_asst_svc.get_assistants.return_value = None
        mock_asst_svc.get_assistant.side_effect = None
        mock_asst_svc.get_assistant.return_value = None
        mock_asst_svc.create_assistant.side_effect = None
        mock_asst_svc.create_assistant.return_value = None
        mock_asst_svc.update_assistant.side_effect = None
        mock_asst_svc.update_assistant.return_value = None
        mock_asst_svc.delete_assistant.side_effect = None
        mock_asst_svc.delete_assistant.return_value = None
        mock_asst_svc.upload_avatar.side_effect = None
        mock_asst_svc.upload_avatar.return_value = None
        mock_asst_svc.remove_avatar.side_effect = None
        mock_asst_svc.remove_avatar.return_value = None
        mock_asst_svc.get_avatar_path.side_effect = None
        mock_asst_svc.get_avatar_path.return_value = None
        mock_asst_svc.clear_cache.side_effect = None
        mock_asst_svc.clear_cache.return_value = None

    def test_get_assistants(self):
        """Test listing assistants."""
        mock_asst_svc.get_assistants.return_value = []

        response = client.get("/api/v1/assistants/")

        assert response.status_code == 200
        assert response.json() == []
        mock_asst_svc.get_assistants.assert_called_once()

    def test_get_assistants_error(self):
        """Test listing assistants error."""
        mock_asst_svc.get_assistants.side_effect = Exception("error")

        response = client.get("/api/v1/assistants/")

        assert response.status_code == 500
        assert "Failed to fetch assistants" in response.json()["message"]

    def test_get_assistant_public(self):
        """Test public assistant access."""
        asst_id = uuid4()

        asst_mock = AssistantResponse(
            id=asst_id,
            name="Test Bot",
            description="Desc",
            avatar_bg_color="#000000",
            avatar_text_color="white",
            instructions="Instructions",
            model=AIModel.OPENAI,
            use_reranker=False,
            top_k_retrieval=25,
            top_n_rerank=5,
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            linked_connectors=[],
        )

        mock_asst_svc.get_assistant.return_value = asst_mock

        response = client.get(f"/api/v1/assistants/{str(asst_id)}")

        assert response.status_code == 200
        assert response.json()["id"] == str(asst_id)

    def test_get_assistant_not_found(self):
        """Test assistant not found."""
        asst_id = uuid4()
        mock_asst_svc.get_assistant.return_value = None

        response = client.get(f"/api/v1/assistants/{str(asst_id)}")

        assert response.status_code == 404

    def test_get_assistant_error(self):
        """Test assistant fetch error."""
        asst_id = uuid4()
        mock_asst_svc.get_assistant.side_effect = Exception("error")

        response = client.get(f"/api/v1/assistants/{str(asst_id)}")

        assert response.status_code == 500

    def test_get_assistant_protected_denied(self):
        """Test protected assistant 401 without user."""
        asst_id = uuid4()
        asst_mock = MagicMock(spec=AssistantResponse)
        asst_mock.user_authentication = True
        asst_mock.name = "Secure Bot"

        mock_asst_svc.get_assistant.return_value = asst_mock

        # Default override returns None for user
        response = client.get(f"/api/v1/assistants/{str(asst_id)}")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

    def test_create_assistant(self):
        """Test creation delegate."""
        data = {"name": "New Bot", "model": "openai", "instructions": "Be helpful", "configuration": {}}

        asst_id = uuid4()
        mock_resp = AssistantResponse(
            id=asst_id,
            name=data["name"],
            description=None,
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions=data["instructions"],
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            linked_connectors=[],
        )

        mock_asst_svc.create_assistant.return_value = mock_resp

        response = client.post("/api/v1/assistants/", json=data)

        assert response.status_code == 201
        mock_asst_svc.create_assistant.assert_called_once()

    def test_create_assistant_error(self):
        """Test creation error."""
        data = {"name": "New Bot", "model": "openai", "instructions": "Be helpful", "configuration": {}}
        mock_asst_svc.create_assistant.side_effect = Exception("error")

        response = client.post("/api/v1/assistants/", json=data)

        assert response.status_code == 500

    def test_update_assistant(self):
        """Test update assistant."""
        asst_id = uuid4()
        data = {"name": "Updated Bot"}

        mock_resp = AssistantResponse(
            id=asst_id,
            name="Updated Bot",
            description=None,
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions="Be helpful",
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            linked_connectors=[],
        )
        mock_asst_svc.update_assistant.return_value = mock_resp

        response = client.put(f"/api/v1/assistants/{asst_id}", json=data)

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Bot"

    def test_update_assistant_not_found(self):
        """Test update assistant not found."""
        asst_id = uuid4()
        data = {"name": "Updated Bot"}
        mock_asst_svc.update_assistant.return_value = None

        response = client.put(f"/api/v1/assistants/{asst_id}", json=data)

        assert response.status_code == 404

    def test_delete_assistant(self):
        """Test delete assistant."""
        asst_id = uuid4()
        mock_asst_svc.delete_assistant.return_value = True

        response = client.delete(f"/api/v1/assistants/{asst_id}")

        assert response.status_code == 204

    def test_delete_assistant_not_found(self):
        """Test delete assistant not found."""
        asst_id = uuid4()
        mock_asst_svc.delete_assistant.return_value = False

        response = client.delete(f"/api/v1/assistants/{asst_id}")

        assert response.status_code == 404

    def test_upload_avatar(self):
        """Test upload avatar."""
        asst_id = uuid4()
        file_content = b"fake image content"
        file = io.BytesIO(file_content)

        mock_resp = AssistantResponse(
            id=asst_id,
            name="Bot",
            avatar_image="avatar.png",
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions="Instructions",
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_asst_svc.upload_avatar.return_value = mock_resp

        response = client.post(
            f"/api/v1/assistants/{asst_id}/avatar", files={"file": ("avatar.png", file, "image/png")}
        )

        assert response.status_code == 200
        assert response.json()["avatar_image"] == "avatar.png"

    def test_delete_avatar(self):
        """Test delete avatar."""
        asst_id = uuid4()
        mock_resp = AssistantResponse(
            id=asst_id,
            name="Bot",
            avatar_image=None,
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions="Instructions",
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_asst_svc.remove_avatar.return_value = mock_resp

        response = client.delete(f"/api/v1/assistants/{asst_id}/avatar")

        assert response.status_code == 200
        assert response.json()["avatar_image"] is None

    def test_get_avatar(self):
        """Test get avatar."""
        asst_id = uuid4()
        asst_mock = AssistantResponse(
            id=asst_id,
            name="Bot",
            avatar_image="avatar.png",
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions="Instructions",
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_asst_svc.get_assistant.return_value = asst_mock
        mock_asst_svc.get_avatar_path.return_value = "fake/path/avatar.png"

        # Mock FileResponse
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.api.v1.endpoints.assistants.FileResponse", lambda path: {"path": path})
            response = client.get(f"/api/v1/assistants/{asst_id}/avatar")

        assert response.status_code == 200
        assert response.json()["path"] == "fake/path/avatar.png"

    def test_get_avatar_not_found(self):
        """Test get avatar not found."""
        asst_id = uuid4()
        mock_asst_svc.get_assistant.return_value = None

        response = client.get(f"/api/v1/assistants/{asst_id}/avatar")

        assert response.status_code == 404

    def test_get_avatar_protected_denied(self):
        """Test get avatar protected denied."""
        asst_id = uuid4()
        asst_mock = AssistantResponse(
            id=asst_id,
            name="Bot",
            avatar_image="avatar.png",
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions="Instructions",
            user_authentication=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_asst_svc.get_assistant.return_value = asst_mock

        response = client.get(f"/api/v1/assistants/{asst_id}/avatar")

        assert response.status_code == 404
        assert "Avatar not found" in response.json()["message"]

    def test_get_avatar_file_not_found(self):
        """Test get avatar file not found."""
        asst_id = uuid4()
        asst_mock = AssistantResponse(
            id=asst_id,
            name="Bot",
            avatar_image="avatar.png",
            avatar_bg_color="#000000",
            avatar_text_color="white",
            model=AIModel.OPENAI,
            instructions="Instructions",
            user_authentication=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_asst_svc.get_assistant.return_value = asst_mock
        mock_asst_svc.get_avatar_path.return_value = None

        response = client.get(f"/api/v1/assistants/{asst_id}/avatar")

        assert response.status_code == 404

    def test_clear_cache(self):
        """Test clear cache."""
        asst_id = uuid4()
        mock_asst_svc.clear_cache.return_value = 5

        response = client.delete(f"/api/v1/assistants/{asst_id}/cache")

        assert response.status_code == 200
        assert response.json()["deleted_count"] == 5

    def test_clear_cache_error(self):
        """Test clear cache error."""
        asst_id = uuid4()
        mock_asst_svc.clear_cache.side_effect = Exception("error")

        response = client.delete(f"/api/v1/assistants/{asst_id}/cache")

        assert response.status_code == 500
