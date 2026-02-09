from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints.chat import router
from app.models.user import User
from app.services.assistant_service import (AssistantService,
                                            get_assistant_service)
from app.services.chat_service import ChatService, get_chat_service
from app.core.database import get_db
from app.core.exceptions import VectraException
from app.main import global_exception_handler

app = FastAPI()
app.include_router(router, prefix="/api/v1/chat")

# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(VectraException, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)

# Mocks
mock_chat_svc = AsyncMock(spec=ChatService)
mock_asst_svc = AsyncMock(spec=AssistantService)
mock_db = AsyncMock()


async def override_get_chat_service():
    return mock_chat_svc


async def override_get_assistant_service():
    return mock_asst_svc

async def override_get_db():
    return mock_db


app.dependency_overrides[get_chat_service] = override_get_chat_service
app.dependency_overrides[get_assistant_service] = override_get_assistant_service
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestChat:

    def setup_method(self):
        mock_chat_svc.reset_mock()
        mock_asst_svc.reset_mock()
        mock_db.reset_mock()
        # Ensure chat_repository exists on the mock
        mock_chat_svc.chat_repository = AsyncMock()

    def test_chat_stream_success_public(self):
        """Test public assistant access."""
        # Setup Assistant Mock
        asst = MagicMock()
        asst.id = uuid4()
        asst.user_authentication = False
        mock_asst_svc.get_assistant_model.return_value = asst

        # Setup Chat Mock (stream_chat is an async generator)
        async def async_gen(*args, **kwargs):
            yield "data"

        # Configure the AsyncMock to return the generator
        mock_chat_svc.stream_chat.side_effect = async_gen

        data = {"message": "Hello", "assistant_id": str(asst.id), "session_id": "test-session"}

        response = client.post("/api/v1/chat/stream", json=data)

        assert response.status_code == 200
        mock_asst_svc.get_assistant_model.assert_called_once()
        mock_chat_svc.stream_chat.assert_called_once()

    def test_chat_stream_auth_required_denied(self):
        """Test protected assistant access denied."""
        asst = MagicMock()
        asst.id = uuid4()
        asst.user_authentication = True
        mock_asst_svc.get_assistant_model.return_value = asst

        data = {"message": "Hello", "assistant_id": str(asst.id), "session_id": "test-session"}

        response = client.post("/api/v1/chat/stream", json=data)
        assert response.status_code == 401

    def test_chat_stream_assistant_not_found(self):
        mock_asst_svc.get_assistant_model.return_value = None
        data = {"message": "Hello", "assistant_id": str(uuid4()), "session_id": "test-session"}
        response = client.post("/api/v1/chat/stream", json=data)
        assert response.status_code == 404

    def test_reset_session(self):
        """Test reset."""
        session_id = "abc"
        mock_chat_svc.reset_conversation.return_value = None

        response = client.delete(f"/api/v1/chat/{session_id}")
        assert response.status_code == 200
        mock_chat_svc.reset_conversation.assert_called_once_with(session_id)

    def test_get_chat_history(self):
        """Test get chat history."""
        session_id = "test-session"
        mock_msg = MagicMock()
        mock_msg.id = uuid4()
        mock_msg.content = "Hello"
        mock_msg.role = "user"
        mock_msg.metadata_ = {
            "sources": [{"id": "1", "text": "source content", "metadata": {"file_name": "test.pdf"}}],
            "steps": [{"label": "Step 1", "step_type": "thought"}],
            "visualization": {"viz_type": "pie", "series": ["10", "20"]}
        }
        
        mock_chat_svc.chat_repository.get_messages.return_value = [mock_msg]
        
        response = client.get(f"/api/v1/chat/{session_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 1
        assert data["messages"][0]["text"] == "Hello"
        assert data["messages"][0]["sources"][0]["type"] == "pdf"
        assert data["messages"][0]["visualization"]["series"] == [10.0, 20.0]

    def test_get_chat_history_with_complex_metadata(self):
        session_id = "test-session"
        mock_msg = MagicMock()
        mock_msg.id = uuid4()
        mock_msg.content = "Hello"
        mock_msg.role = "bot"
        mock_msg.metadata_ = {
            "sources": [
                {"id": "1", "text": "source1", "metadata": {"file_name": "test.docx"}},
                {"id": "2", "text": "source2", "metadata": {"name": "test.txt"}}
            ],
            "steps": [
                {"step_type": "thought", "metadata": {"is_substep": True}},
                {"label": "Step 2"}
            ],
            "visualization": {
                "viz_type": "pie",
                "series": [
                    {"data": [{"y": "10.5"}, {"y": "invalid"}]}
                ]
            }
        }
        mock_chat_svc.chat_repository.get_messages.return_value = [mock_msg]
        
        response = client.get(f"/api/v1/chat/{session_id}/history")
        assert response.status_code == 200
        data = response.json()
        msg = data["messages"][0]
        assert msg["sources"][0]["type"] == "docx"
        assert msg["sources"][1]["name"] == "test.txt"
        assert msg["steps"][0]["label"] == "Thought"
        assert msg["steps"][0]["isSubStep"] is True
        assert msg["visualization"]["series"][0]["data"][0]["y"] == 10.5
        assert msg["visualization"]["series"][0]["data"][1]["y"] == 0.0

    def test_ping(self):
        response = client.get("/api/v1/chat/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "Backend is alive"}

    def test_test_db(self):
        response = client.get("/api/v1/chat/test-db")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "connected"}

    def test_test_assistant_svc(self):
        response = client.get("/api/v1/chat/test-assistant-service")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "injected"}

    @patch("app.api.v1.endpoints.chat.get_current_user")
    def test_chat_stream_with_user(self, mock_get_current_user):
        """Test assistant access with authenticated user."""
        # Setup User
        user = MagicMock(spec=User)
        user.id = uuid4()
        mock_get_current_user.return_value = user
        
        # Setup Assistant Mock
        asst = MagicMock()
        asst.id = uuid4()
        asst.user_authentication = True
        mock_asst_svc.get_assistant_model.return_value = asst

        # Setup Chat Mock
        async def async_gen(*args, **kwargs):
            yield "data"
        mock_chat_svc.stream_chat.side_effect = async_gen

        data = {"message": "Hello", "assistant_id": str(asst.id), "session_id": "test-session"}
        
        # We need to provide a Bearer token to trigger get_optional_user logic
        headers = {"Authorization": "Bearer some-token"}
        response = client.post("/api/v1/chat/stream", json=data, headers=headers)

        assert response.status_code == 200
        mock_chat_svc.stream_chat.assert_called_once()
        # Verify user_id was passed correctly
        args, kwargs = mock_chat_svc.stream_chat.call_args
        assert kwargs["user_id"] == str(user.id)

    def test_debug_stream(self):
        asst = MagicMock()
        asst.id = uuid4()
        mock_asst_svc.get_assistant_model.return_value = asst

        async def async_gen(*args, **kwargs):
            yield "event1"
            yield "event2"
        mock_chat_svc.stream_chat.side_effect = async_gen

        data = {"message": "Hello", "assistant_id": str(asst.id), "session_id": "test-session"}
        response = client.post("/api/v1/chat/debug-stream", json=data)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["first_event"] == "event1"

    def test_debug_stream_assistant_not_found(self):
        mock_asst_svc.get_assistant_model.return_value = None
        data = {"message": "Hello", "assistant_id": str(uuid4()), "session_id": "test-session"}
        response = client.post("/api/v1/chat/debug-stream", json=data)
        assert response.status_code == 200
        assert response.json() == {"error": "Assistant not found"}

    def test_debug_stream_no_events(self):
        asst = MagicMock()
        asst.id = uuid4()
        mock_asst_svc.get_assistant_model.return_value = asst

        async def async_gen(*args, **kwargs):
            if False: yield "nothing"
        mock_chat_svc.stream_chat.side_effect = async_gen

        data = {"message": "Hello", "assistant_id": str(asst.id), "session_id": "test-session"}
        response = client.post("/api/v1/chat/debug-stream", json=data)
        assert response.status_code == 200
        assert response.json() == {"error": "No events yielded"}
