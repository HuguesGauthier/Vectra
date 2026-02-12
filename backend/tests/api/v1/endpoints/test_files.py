from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.files import router
from app.core.exceptions import EntityNotFound, TechnicalError, VectraException
from app.core.security import get_current_user
from app.main import global_exception_handler
from app.models.user import User
from app.schemas.files import FileStreamingInfo
from app.services.file_service import FileService, get_file_service

app = FastAPI()
# Add global exception handler to test JSON response format
app.add_exception_handler(VectraException, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(router, prefix="/api/v1/files")

# Mocks
mock_file_svc = AsyncMock(spec=FileService)


async def override_get_file_service():
    return mock_file_svc


def override_get_user():
    return User(id=uuid4(), email="user@test.com", is_superuser=False)


app.dependency_overrides[get_file_service] = override_get_file_service
app.dependency_overrides[get_current_user] = override_get_user

# Disable raising server exceptions to test the global handler's response
client = TestClient(app, raise_server_exceptions=False)


class TestFiles:

    def setup_method(self):
        mock_file_svc.reset_mock()

    def test_stream_file_success(self):
        """Test file streaming initiation (Happy Path)."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.return_value = FileStreamingInfo(
            file_path=__file__, media_type="text/x-python", file_name="test_files.py"
        )

        response = client.get(f"/api/v1/files/stream/{doc_id}")

        assert response.status_code == 200
        assert "text/x-python" in response.headers["content-type"]
        mock_file_svc.get_file_for_streaming.assert_called_once()

    def test_stream_file_not_found(self):
        """Test non-existent file (Error Case)."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.side_effect = EntityNotFound("Document not found")

        response = client.get(f"/api/v1/files/stream/{doc_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "entity_not_found"
        assert "Document not found" in data["message"]

    def test_stream_file_technical_error(self):
        """Test technical error handling."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.side_effect = TechnicalError(
            message="Storage failure", error_code="storage_error"
        )

        response = client.get(f"/api/v1/files/stream/{doc_id}")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "storage_error"
        assert "Storage failure" in data["message"]

    def test_stream_file_unexpected_error(self):
        """Test unexpected exception wrapping."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.side_effect = Exception("Crash")

        response = client.get(f"/api/v1/files/stream/{doc_id}")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "file_streaming_error"
        assert "Could not stream file" in data["message"]
