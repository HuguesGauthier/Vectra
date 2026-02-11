import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.gemini_vision_service import GeminiVisionService
from app.core.exceptions import ConfigurationError, ExternalDependencyError


@pytest.fixture
def mock_client():
    client = MagicMock()
    # Mock files.upload and files.delete
    client.files.upload = MagicMock()
    client.files.delete = MagicMock()
    # Mock models.generate_content
    client.models.generate_content = MagicMock()
    return client


@pytest.fixture
def mock_settings_service():
    service = AsyncMock()
    service.get_value.return_value = "gemini-1.5-flash"
    return service


@pytest.fixture
def vision_service(mock_client, mock_settings_service):
    return GeminiVisionService(mock_client, mock_settings_service)


@pytest.mark.asyncio
async def test_analyze_image_success(vision_service, mock_client):
    # Setup
    mock_file = MagicMock()
    mock_file.name = "files/test-file-id"
    mock_client.files.upload.return_value = mock_file

    mock_response = MagicMock()
    mock_response.text = "A beautiful sunset."
    mock_client.models.generate_content.return_value = mock_response

    # Execute
    result = await vision_service.analyze_image("path/to/image.jpg")

    # Assert
    assert result == "A beautiful sunset."
    mock_client.files.upload.assert_called_once_with(path="path/to/image.jpg")
    mock_client.models.generate_content.assert_called_once()
    mock_client.files.delete.assert_called_once_with(name="files/test-file-id")


@pytest.mark.asyncio
async def test_analyze_image_config_error(vision_service, mock_settings_service):
    # Setup
    mock_settings_service.get_value.return_value = None

    # Execute & Assert
    with pytest.raises(ConfigurationError, match="gemini_vision_model is not configured"):
        await vision_service.analyze_image("path/to/image.jpg")


@pytest.mark.asyncio
async def test_analyze_image_cleanup_on_failure(vision_service, mock_client):
    # Setup
    mock_file = MagicMock()
    mock_file.name = "files/fail-file-id"
    mock_client.files.upload.return_value = mock_file

    mock_client.models.generate_content.side_effect = Exception("API Error")

    # Execute & Assert
    with pytest.raises(ExternalDependencyError):
        await vision_service.analyze_image("path/to/image.jpg")

    # Ensure cleanup still happened
    mock_client.files.delete.assert_called_once_with(name="files/fail-file-id")
