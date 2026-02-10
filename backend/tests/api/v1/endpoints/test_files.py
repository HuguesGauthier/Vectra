from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.files import router
from app.core.exceptions import EntityNotFound, TechnicalError
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.files import FileStreamingInfo
from app.services.file_service import FileService, get_file_service

app = FastAPI()
app.include_router(router, prefix="/api/v1/files")

# Mocks
mock_file_svc = AsyncMock(spec=FileService)


async def override_get_file_service():
    return mock_file_svc


def override_get_user():
    return User(id=uuid4(), email="user@test.com", is_superuser=False)


app.dependency_overrides[get_file_service] = override_get_file_service
app.dependency_overrides[get_current_user] = override_get_user

client = TestClient(app)


class TestFiles:

    def setup_method(self):
        mock_file_svc.reset_mock()

    def test_stream_file_success(self):
        """Test file streaming initiation."""
        doc_id = uuid4()
        # Mock what get_file_for_streaming returns: FileStreamingInfo
        # Use existing file such as this one to pass os.stat checks inside FileResponse
        mock_file_svc.get_file_for_streaming.return_value = FileStreamingInfo(
            file_path=__file__, media_type="text/x-python", file_name="test_files.py"
        )

        response = client.get(f"/api/v1/files/stream/{doc_id}")

        assert response.status_code == 200
        # Starlette FileResponse sets content-type
        assert "text/x-python" in response.headers["content-type"]
        mock_file_svc.get_file_for_streaming.assert_called_once()

    def test_stream_file_not_found(self):
        """Test non-existent file."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.side_effect = EntityNotFound("Missing")

        # In this minimal app instance, we don't have exception handlers loaded,
        # so check if exception is raised directly.
        with pytest.raises(EntityNotFound):
            client.get(f"/api/v1/files/stream/{doc_id}")

    def test_stream_file_technical_error(self):
        """Test technical error."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.side_effect = TechnicalError("Error", error_code="SOME_ERROR")

        with pytest.raises(TechnicalError):
            client.get(f"/api/v1/files/stream/{doc_id}")

    def test_stream_file_unexpected_error(self):
        """Test unexpected error."""
        doc_id = uuid4()
        mock_file_svc.get_file_for_streaming.side_effect = Exception("Unexpected")

        with pytest.raises(TechnicalError) as exc_info:
            client.get(f"/api/v1/files/stream/{doc_id}")
        assert "Could not stream file" in str(exc_info.value)
