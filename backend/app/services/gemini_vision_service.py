import asyncio
import logging
from typing import Annotated, Callable, Optional

from fastapi import Depends
from google import genai

from app.core.exceptions import ConfigurationError, ExternalDependencyError, TechnicalError
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
        gemini_file = None
        try:
            # 1. Get Model Configuration (from settings or sensible default)
            model_name = await self.settings_service.get_value("gemini_vision_model", default="gemini-1.5-flash")

            if callback:
                callback(f"Analyzing image with {model_name}...")

            # 2. Upload File to Gemini Storage
            # We use the File API as it's more robust for multimodal input.
            gemini_file = await asyncio.to_thread(self.client.files.upload, file=image_path)

            # 3. Generate Content
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_name,
                contents=[VISION_PROMPT, gemini_file],
            )

            return response.text if response.text else "No description generated."

        except Exception as e:
            if not isinstance(e, (ConfigurationError, ExternalDependencyError, TechnicalError)):
                logger.error(f"Gemini Vision Error: {e}", exc_info=True)
                raise ExternalDependencyError(
                    f"Image analysis failed: {str(e)}", service="gemini_vision", error_code="VISION_ERROR"
                ) from e
            raise
        finally:
            # P0: Resource Cleanup
            # Ensure the file is deleted from Gemini storage to avoid accumulation.
            if gemini_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=gemini_file.name)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup Gemini file {gemini_file.name}: {cleanup_error}")


# --- Dependency Injection ---


async def get_gemini_client(settings_service: Annotated[SettingsService, Depends()]) -> genai.Client:
    """Provider for Gemini Client using DB-aware settings."""
    api_key = await settings_service.get_value("gemini_api_key")
    if not api_key:
        logger.warning("GEMINI_API_KEY could not be resolved from DB or Env. Vision service is dormant.")
        raise TechnicalError("Gemini API Key missing", error_code="GEMINI_CONFIG_ERROR")
    return genai.Client(api_key=api_key)


async def get_gemini_vision_service(
    client: Annotated[genai.Client, Depends(get_gemini_client)],
    settings_service: Annotated[SettingsService, Depends()],
) -> GeminiVisionService:
    return GeminiVisionService(client, settings_service)
