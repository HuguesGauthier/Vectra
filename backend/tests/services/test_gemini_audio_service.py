import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.services.gemini_audio_service import (GeminiAudioService,
                                               TranscriptionChunk,
                                               TranscriptionResponse)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def audio_service(mock_client):
    return GeminiAudioService(mock_client)


@pytest.mark.asyncio
async def test_transcribe_file_success(audio_service, mock_client):
    # Setup
    mock_file = MagicMock()
    mock_file.state.name = "SUCCESS"
    mock_file.name = "files/test-audio"

    mock_response = MagicMock()
    mock_response.text = '{"segments": [{"timestamp_start": "00:05", "speaker": "A", "text": "Hello world"}]}'

    with patch("asyncio.to_thread", AsyncMock()) as mock_thread:
        with patch(
            "app.services.settings_service.SettingsService.get_value", AsyncMock(return_value="gemini-1.5-flash")
        ):

            def to_thread_side_effect(func, *args, **kwargs):
                if func == os.path.getsize:
                    return 1024
                return mock_file if "upload" in str(func) or "get" in str(func) else mock_response

            mock_thread.side_effect = to_thread_side_effect

            # Execute
            result = await audio_service.transcribe_file("path/to/audio.mp3")

            # Verify
            assert len(result) == 1
            assert result[0].text == "Hello world"
            assert result[0].speaker == "A"
            assert result[0].start_seconds == 5

            assert mock_thread.call_count >= 3


@pytest.mark.asyncio
async def test_transcribe_file_timeout(audio_service, mock_client):
    # Setup
    mock_file = MagicMock()
    mock_file.state.name = "PROCESSING"

    audio_service.MAX_POLLING_DURATION_SECONDS = 0.1  # Short timeout
    audio_service.POLLING_INTERVAL_SECONDS = 0.05

    def to_thread_side_effect(func, *args, **kwargs):
        if func == os.path.getsize:
            return 1024
        return mock_file

    # Mock time.time to advance by 0.06 on each call to ensure loop terminates
    # The while loop calls time.time() at line 95.
    with patch("time.time", side_effect=[100.0, 100.0, 100.15, 100.2, 100.3]):
        with patch("asyncio.to_thread", AsyncMock(side_effect=to_thread_side_effect)):
            with patch("asyncio.sleep", AsyncMock()):
                with patch(
                    "app.services.settings_service.SettingsService.get_value",
                    AsyncMock(return_value="gemini-1.5-flash"),
                ):
                    # Execute & Verify
                    with pytest.raises(TechnicalError) as exc:
                        await audio_service.transcribe_file("path/to/audio.mp3")
                    assert exc.value.error_code == "GEMINI_TIMEOUT"


def test_parse_timestamp_to_seconds(audio_service):
    assert audio_service._parse_timestamp_to_seconds("[00:10]") == 10
    assert audio_service._parse_timestamp_to_seconds("01:05") == 65
    assert audio_service._parse_timestamp_to_seconds("01:02:03") == 3723
    assert audio_service._parse_timestamp_to_seconds("invalid") == 0
