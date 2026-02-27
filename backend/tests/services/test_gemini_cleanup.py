import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.gemini_vision_service import GeminiVisionService
from app.services.gemini_audio_service import GeminiAudioService


@pytest.mark.asyncio
async def test_gemini_vision_uses_exact_model_name():
    """Verify that GeminiVisionService uses exactly the model ID from settings."""
    settings_service = AsyncMock()
    # Mocking exactly what the user might have in their catalog
    settings_service.get_value.return_value = "gemini-2.5-flash"

    client = MagicMock()
    service = GeminiVisionService(client, settings_service)

    with patch("asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = MagicMock()
        await service.analyze_image("test.jpg")

        # Check call to generate_content
        calls = [call for call in mock_to_thread.call_args_list if call[0][0] == client.models.generate_content]
        assert len(calls) > 0
        _, kwargs = calls[0]
        assert kwargs["model"] == "gemini-2.5-flash"
        # Verify NO suffixes like -latest were added
        assert "-latest" not in kwargs["model"]


@pytest.mark.asyncio
async def test_gemini_audio_uses_exact_model_name():
    """Verify that GeminiAudioService uses exactly the model ID from settings."""
    settings_service = AsyncMock()
    settings_service.get_value.return_value = "gemini-2.5-pro"

    client = MagicMock()
    # Mock files.upload
    mock_file = MagicMock()
    mock_file.name = "audio_123"
    mock_file.state.name = "ACTIVE"
    client.files.upload.return_value = mock_file
    client.files.get.return_value = mock_file  # For polling

    # Mock models.generate_content
    mock_response = MagicMock()
    mock_response.text = '{"chunks": []}'
    client.models.generate_content.return_value = mock_response

    service = GeminiAudioService(client, settings_service)

    with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)):
        # Let real Pydantic validation run by providing valid JSON
        # AND patch os.path.getsize which is called at line 85 of gemini_audio_service.py
        with patch("os.path.getsize", return_value=1024):
            mock_response.text = '{"segments": []}'
            await service.transcribe_file("test.mp3")

        # Verify call to generate_content
        assert client.models.generate_content.called
        _, kwargs = client.models.generate_content.call_args
        assert kwargs["model"] == "gemini-2.5-pro"
