import asyncio
import logging
import os
import time
from typing import Annotated, Callable, List, Optional

from fastapi import Depends
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.core.settings import get_settings
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# --- Constants ---
TRANSCRIPTION_PROMPT = """
Transcribe this audio file. 
Identify speakers. 
Output valid JSON matching this schema:
{
  "segments": [
    {"timestamp_start": "MM:SS", "speaker": "Speaker 1", "text": "Content..."}
  ]
}
"""


# --- Schemas for Structured Output ---
class TranscriptionSegment(BaseModel):
    timestamp_start: str
    speaker: str
    text: str


class TranscriptionResponse(BaseModel):
    segments: List[TranscriptionSegment]


class TranscriptionChunk(BaseModel):
    timestamp_start: str
    timestamp_end: str
    speaker: str
    text: str
    start_seconds: int
    timestamp_display: str


class GeminiAudioService:
    """
    Architect Refactor of GeminiAudioService.
    Hardens architecture via modern DI (P1) and non-blocking IO (P0).
    """

    # Safety Timouts
    POLLING_INTERVAL_SECONDS = 5
    MAX_POLLING_DURATION_SECONDS = 600  # 10 minutes max waiting for processing

    def __init__(self, client: genai.Client, settings_service: SettingsService) -> None:
        """
        Fixes P1: Injects genai.Client and SettingsService instead of internal lifecycle management.
        """
        self.client = client
        self.settings_service = settings_service

    async def transcribe_file(
        self, file_path: str, callback: Optional[Callable[[str], None]] = None
    ) -> List[TranscriptionChunk]:
        """
        Transcribes audio files using Gemini with structured output.
        Fixes P0: Uses non-blocking IO for file size checks.
        """
        func_name = "GeminiAudioService.transcribe_file"
        start_time = time.time()
        audio_file = None

        try:
            # 1. Upload
            if callback:
                callback("Uploading audio to Gemini...")

            # 🔴 P0: Non-blocking file size check
            file_size = await asyncio.to_thread(os.path.getsize, file_path)
            logger.info(f"START | {func_name} | File: {os.path.basename(file_path)} | Size: {file_size/1e6:.1f}MB")

            audio_file = await asyncio.to_thread(
                self.client.files.upload, file=file_path, config={"display_name": os.path.basename(file_path)}
            )

            # 2. Wait for Processing (With Timeout)
            if callback:
                callback("Processing audio...")

            processing_start = time.time()
            while audio_file.state.name == "PROCESSING":
                if time.time() - processing_start > self.MAX_POLLING_DURATION_SECONDS:
                    raise TechnicalError("Gemini processing timed out", error_code="GEMINI_TIMEOUT")

                await asyncio.sleep(self.POLLING_INTERVAL_SECONDS)
                audio_file = await asyncio.to_thread(self.client.files.get, name=audio_file.name)

            if audio_file.state.name == "FAILED":
                raise TechnicalError("Gemini failed to process audio", error_code="GEMINI_PROCESSING_FAILED")

            # 3. Generate Transcription (JSON Mode)
            if callback:
                callback("Generating transcription...")

            model_name = await self.settings_service.get_value("gemini_transcription_model")
            if not model_name:
                raise ConfigurationError("gemini_transcription_model is not configured in settings")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=[TRANSCRIPTION_PROMPT, audio_file],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=TranscriptionResponse, temperature=0.0
                ),
            )

            # 4. Parse & Validate
            if not response.text:
                logger.warning(f"EMPTY_RESPONSE | {func_name} | Doc: {audio_file.name}")
                return []

            # Using Pydantic for validation
            parsed_data = TranscriptionResponse.model_validate_json(response.text)

            # 5. Convert to internal format
            chunks = []
            for segment in parsed_data.segments:
                chunks.append(
                    TranscriptionChunk(
                        timestamp_start=segment.timestamp_start,
                        timestamp_end="",
                        speaker=segment.speaker or "Unknown",
                        text=segment.text,
                        start_seconds=self._parse_timestamp_to_seconds(segment.timestamp_start),
                        timestamp_display=segment.timestamp_start,
                    )
                )

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"SUCCESS | {func_name} | {len(chunks)} segments | {elapsed}ms")
            return chunks

        except ValidationError as ve:
            logger.error(f"PARSE_ERROR | {func_name} | Error: {ve}")
            raise TechnicalError("Gemini returned invalid JSON structure", error_code="GEMINI_PARSE_ERROR")

        except Exception as e:
            logger.error(f"FAILURE | {func_name} | Error: {e}", exc_info=True)
            if isinstance(e, (TechnicalError, ExternalDependencyError)):
                raise e
            raise ExternalDependencyError(f"Transcription failed: {str(e)}", error_code="TRANSCRIPTION_ERROR")

        finally:
            if audio_file:
                # 🟠 P1: Supervised background cleanup
                asyncio.create_task(self._safe_delete(audio_file.name))

    async def _safe_delete(self, file_name: str):
        """Non-blocking background deletion."""
        try:
            await asyncio.to_thread(self.client.files.delete, name=file_name)
            logger.debug(f"CLEANUP_SUCCESS | Gemini file: {file_name}")
        except Exception as e:
            logger.warning(f"CLEANUP_FAIL | Gemini file: {file_name} | Error: {e}")

    def _parse_timestamp_to_seconds(self, timestamp: str) -> int:
        """
        Parses [MM:SS] or [HH:MM:SS] into total seconds.
        Fixes P3: Robust parsing for magic strings.
        """
        try:
            clean_ts = timestamp.replace("[", "").replace("]", "").strip()
            parts = list(map(int, clean_ts.split(":")))

            if len(parts) == 2:  # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:  # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            return 0
        except (ValueError, IndexError):
            logger.warning(f"PARSING_ERROR | Invalid timestamp format: {timestamp}")
            return 0


# 🟠 P1: Modern FastAPI Dependency Injection
def get_gemini_client() -> genai.Client:
    """Provider for Gemini Client."""
    s = get_settings()
    if not s.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Audio service is dormant.")
        raise TechnicalError("Gemini API Key missing", error_code="GEMINI_CONFIG_ERROR")
    return genai.Client(api_key=s.GEMINI_API_KEY)


async def get_gemini_audio_service(
    client: Annotated[genai.Client, Depends(get_gemini_client)], settings_service: Annotated[SettingsService, Depends()]
) -> GeminiAudioService:
    """Dependency provider for GeminiAudioService."""
    return GeminiAudioService(client, settings_service)
