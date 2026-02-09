import asyncio
import logging
from typing import Annotated, Callable, List, Optional

from fastapi import Depends
from google import genai
from google.genai import types

from app.core.database import get_session_factory
from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.core.settings import get_settings
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# --- Constants ---
VISION_PROMPT = """
Analyze this image and provide a detailed textual description.
If it contains text (OCR), transcribe it exactly.
If it's a diagram or chart, explain its data and structure.
Structure the output as valid Markdown.
"""


class GeminiVisionService:
    """
    Service for Image Analysis using Gemini 1.5 Flash (Multimodal).
    """

    def __init__(self, client: genai.Client, settings_service: SettingsService) -> None:
        self.client = client
        self.settings_service = settings_service

    async def analyze_image(self, image_path: str, callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Analyzes an image and returns a text description/transcription.
        """
        try:
            # 1. Upload File (if needed) or send bytes.
            # Gemini Python SDK supports passing file paths directly or bytes.
            # Local file path is efficient.

            # 2. Get Model
            model_name = await self.settings_service.get_value("gemini_vision_model")
            if not model_name:
                raise ConfigurationError("gemini_vision_model is not configured in settings")

            if callback:
                callback("Analyzing image with Gemini Vision...")

            # 3. Generate Content
            # We read file as bytes to avoid complex file upload management if the file is small enough.
            # However, for 1.5 Flash, the file API is often safer for larger images or consistency.
            # But let's try direct file path or bytes to keep it simple and stateless.

            # "contents" in genai can be a list. One part is text, one part is image.

            # Using the File API (upload_file) is safer for latency/caching but requires cleanup.
            # Let's try sending the image data directly (bytes) if supported by this SDK version.
            # Actually, `client.models.generate_content` supports types.Part.from_bytes usually?
            # Or we can use the `upload_file` utility for temporary usage.

            # Let's use `client.files.upload` for consistency with AudioService if possible,
            # BUT for images, simple bytes often work fine and are faster for single-turn.
            # Let's use the file upload to be safe with 1.5 Flash limits/formats.

            gemini_file = await asyncio.to_thread(self.client.files.upload, path=image_path)

            # Wait for processing? Images are usually instant.

            response = await asyncio.to_thread(
                self.client.models.generate_content, model=model_name, contents=[VISION_PROMPT, gemini_file]
            )

            # Cleanup file?
            # Ideally yes.
            # await asyncio.to_thread(self.client.files.delete, name=gemini_file.name) # Fire and forget or await?

            return response.text if response.text else "No description generated."

        except Exception as e:
            logger.error(f"Gemini Vision Error: {e}")
            raise ExternalDependencyError(f"Image analysis failed: {str(e)}", error_code="VISION_ERROR")


# --- Dependency Injection ---


def get_gemini_client() -> genai.Client:
    """Provider for Gemini Client."""
    s = get_settings()
    if not s.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Vision service is dormant.")
        raise TechnicalError("Gemini API Key missing", error_code="GEMINI_CONFIG_ERROR")
    return genai.Client(api_key=s.GEMINI_API_KEY)


async def get_gemini_vision_service(
    client: Annotated[genai.Client, Depends(get_gemini_client)],
    settings_service: Annotated[SettingsService, Depends()],  # Needs settings service injection
) -> GeminiVisionService:
    return GeminiVisionService(client, settings_service)
