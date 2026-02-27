from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from app.core.database import get_session_factory
from app.core.exceptions import TechnicalError
from app.factories.processors.base import DocumentMetadata, FileProcessor, ProcessedDocument
from app.services.gemini_vision_service import GeminiVisionService, get_gemini_client
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class ImageProcessor(FileProcessor):
    """
    Processor for Images (JPG, PNG, etc.) using Gemini 1.5 Flash Vision.
    """

    def __init__(self) -> None:
        # Images can be large, but usually < 20MB. Set limit.
        super().__init__(max_file_size_bytes=20 * 1024 * 1024)

    def get_supported_extensions(self) -> List[str]:
        return ["jpg", "jpeg", "png", "tiff", "bmp", "heic"]

    async def process(self, file_path: str, ai_provider: Optional[str] = None) -> List[ProcessedDocument]:
        """
        Analyze image and return text description.
        """
        path = await self._validate_file_path(file_path)

        # Determine provider: priority to passed provider (connector), then global settings
        provider = ai_provider

        try:
            # DI Injection (Manual)

            session_factory = get_session_factory()

            async with session_factory() as db:
                settings_service = SettingsService(db)

                # If no provider specified by orchestrator, try global embedding_provider
                if not provider:
                    provider = await settings_service.get_value("embedding_provider") or "ollama"

                if provider != "gemini":
                    # Vision is only implemented for Gemini in this system.
                    # For other providers, we skip with a warning for now.
                    logger.warning(f"Vision analysis skipped: Provider {provider} not supported for images.")
                    return []

                client = await get_gemini_client(settings_service)
                service = GeminiVisionService(client, settings_service)

                logger.info(f"Image Processing Started: {path.name} (Provider: {provider})")

                description = await service.analyze_image(str(path))

                # Metadata
                meta: DocumentMetadata = {
                    "file_name": path.name,
                    "file_size": path.stat().st_size,
                    "page_number": 1,
                    "source_type": "image",
                }

                logger.info(f"Image Processing Complete: {path.name}")

                return [ProcessedDocument(content=description, metadata=meta, success=True)]

        except Exception as e:
            logger.error(f"Image Processing Failed: {path.name} | {e}", exc_info=True)
            raise TechnicalError(f"Failed to process image: {e}")
