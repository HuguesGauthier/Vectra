import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.schemas.files import FileStreamingInfo
from app.services.file_service import FileService, get_file_service
from app.core.exceptions import VectraException, EntityNotFound
from app.api.v1.endpoints.audio import router
from app.api.v1.endpoints.chat import get_optional_user


from tests.utils import get_test_app

# Setup FastAPI App for Testing
app = get_test_app()

app.include_router(router, prefix="/api/v1/audio")

# Define Mocks
mock_file_svc = AsyncMock(spec=FileService)


# Helper overrides
async def override_get_file_service():
    return mock_file_svc


async def override_get_optional_user():
    return None


app.dependency_overrides[get_file_service] = override_get_file_service
app.dependency_overrides[get_optional_user] = override_get_optional_user

client = TestClient(app)


class TestAudio:

    def setup_method(self):
        mock_file_svc.reset_mock()
        # Ensure default behavior is reset
        mock_file_svc.get_file_for_streaming = AsyncMock()

    def test_stream_audio_success(self):
        """Test happy path streaming"""
        doc_id = uuid4()

        # We need a real file for FileResponse to not error 500 inside Starlette
        # Using this test file itself
        current_file = os.path.abspath(__file__)

        mock_file_svc.get_file_for_streaming.return_value = FileStreamingInfo(
            file_path=current_file, media_type="text/x-python", file_name="test_audio.py"
        )

        response = client.get(f"/api/v1/audio/stream/{doc_id}")

        assert response.status_code == 200
        # Verify headers/media type if possible, but FileResponse is handled by Starlette
        # Just check we called the service correctly. We expect current_user=None from override.
        mock_file_svc.get_file_for_streaming.assert_called_once_with(doc_id, current_user=None)

    def test_stream_audio_not_found(self):
        """Test 404 behavior"""
        doc_id = uuid4()

        mock_file_svc.get_file_for_streaming.side_effect = EntityNotFound("Not found")

        response = client.get(f"/api/v1/audio/stream/{doc_id}")
        assert response.status_code == 404
        assert response.json()["code"] == "entity_not_found"
        assert response.json()["message"] == "Not found"

    def test_stream_audio_invalid_uuid(self):
        """Test invalid UUID validation by FastAPI"""
        response = client.get(f"/api/v1/audio/stream/not-a-uuid")
        assert response.status_code == 422  # Validation Error

    def test_stream_audio_technical_error(self):
        """Test technical error behavior"""
        doc_id = uuid4()

        mock_file_svc.get_file_for_streaming.side_effect = Exception("Some unexpected error")

        response = client.get(f"/api/v1/audio/stream/{doc_id}")
        assert response.status_code == 500
        assert response.json()["code"] == "technical_error"
        assert "Audio stream failed" in response.json()["message"]
