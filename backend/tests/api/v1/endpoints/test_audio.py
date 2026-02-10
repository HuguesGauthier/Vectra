from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
import os

import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.v1.endpoints.audio import get_file_service, get_optional_user
from app.api.v1.endpoints.audio import \
    router as audio_router  # Import the router and dependencies from audio.py
from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.models.user import User
from app.services.file_service import FileService, FileStreamingInfo

# Create a new FastAPI app for testing and include the audio router
test_app = FastAPI()
test_app.include_router(audio_router, prefix="/v1/audio")
client = TestClient(test_app)


# Add exception handlers to test_app to simulate global exception handling
@test_app.exception_handler(EntityNotFound)
async def entity_not_found_exception_handler(request: Request, exc: EntityNotFound):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.error_code, "message": exc.message, "info": exc.details}},
    )

@test_app.exception_handler(FunctionalError)
async def functional_error_exception_handler(request: Request, exc: FunctionalError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.error_code, "message": exc.message, "info": exc.details}},
    )

@test_app.exception_handler(TechnicalError)
async def technical_error_exception_handler(request: Request, exc: TechnicalError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.error_code, "message": exc.message, "info": exc.details}},
    )


@pytest.fixture
def mock_file_service() -> AsyncMock:
    """Fixture for a mocked FileService."""
    service = AsyncMock(spec=FileService)
    return service


@pytest.fixture
def mock_user() -> AsyncMock:
    """Fixture for a mocked User."""
    user = AsyncMock(spec=User)
    return user


@pytest.mark.asyncio
async def test_stream_audio_success(mock_file_service: AsyncMock, mock_user: AsyncMock, tmp_path) -> None:
    """Tests successful audio streaming via API client."""
    document_id = UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef")
    
    # Create a dummy audio file in a temporary directory
    audio_file_path = tmp_path / "test_audio.mp3"
    audio_file_path.write_text("dummy audio data")

    mock_stream_info = FileStreamingInfo(
        file_path=str(audio_file_path),
        media_type="audio/mpeg",
        file_name="audio.mp3",
    )
    mock_file_service.get_file_for_streaming.return_value = mock_stream_info

    test_app.dependency_overrides[get_file_service] = lambda: mock_file_service
    test_app.dependency_overrides[get_optional_user] = lambda: mock_user

    response = client.get(f"/v1/audio/stream/{document_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["content-disposition"] == 'inline; filename="audio.mp3"'
    assert response.content == b"dummy audio data"

    mock_file_service.get_file_for_streaming.assert_called_once_with(document_id)

    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stream_audio_entity_not_found(mock_file_service: AsyncMock, mock_user: AsyncMock) -> None:
    """Tests audio streaming when the entity is not found via API client."""
    document_id = UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef")
    mock_file_service.get_file_for_streaming.side_effect = EntityNotFound("Document not found")

    test_app.dependency_overrides[get_file_service] = lambda: mock_file_service
    test_app.dependency_overrides[get_optional_user] = lambda: mock_user

    response = client.get(f"/v1/audio/stream/{document_id}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "entity_not_found",
            "message": "Document not found",
            "info": {},
        }
    }
    mock_file_service.get_file_for_streaming.assert_called_once_with(document_id)
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stream_audio_functional_error(mock_file_service: AsyncMock, mock_user: AsyncMock) -> None:
    """Tests audio streaming when a functional error occurs via API client."""
    document_id = UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef")
    mock_file_service.get_file_for_streaming.side_effect = FunctionalError("Functional issue", error_code="TEST_ERROR")

    test_app.dependency_overrides[get_file_service] = lambda: mock_file_service
    test_app.dependency_overrides[get_optional_user] = lambda: mock_user

    response = client.get(f"/v1/audio/stream/{document_id}")

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "TEST_ERROR",
            "message": "Functional issue",
            "info": {},
        }
    }
    mock_file_service.get_file_for_streaming.assert_called_once_with(document_id)
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stream_audio_technical_error(mock_file_service: AsyncMock, mock_user: AsyncMock) -> None:
    """Tests audio streaming when a technical error occurs via API client."""
    document_id = UUID("a1b2c3d4-e5f6-7890-1234-567890abcdef")
    mock_file_service.get_file_for_streaming.side_effect = Exception("Unexpected error")

    test_app.dependency_overrides[get_file_service] = lambda: mock_file_service
    test_app.dependency_overrides[get_optional_user] = lambda: mock_user

    response = client.get(f"/v1/audio/stream/{document_id}")

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "technical_error",
            "message": "Audio stream failed: Unexpected error",
            "info": {},
        }
    }
    mock_file_service.get_file_for_streaming.assert_called_once_with(document_id)
    test_app.dependency_overrides.clear()
