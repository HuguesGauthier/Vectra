"""
Audio Processor - Handles audio transcription using Gemini.

Adapts the GeminiAudioService to the FileProcessor interface.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from app.core.database import get_session_factory
from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.factories.processors.base import DocumentMetadata, FileProcessor, ProcessedDocument
from app.services.gemini_audio_service import GeminiAudioService, get_gemini_client
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class AudioProcessor(FileProcessor):
    """
    Processor for Audio files (MP3, WAV, etc.) using Gemini 1.5 Flash.

    Architecture:
    - Uses GeminiAudioService for heavy lifting (transcription).
    - Returns one document per transcription segment (chunk).
    - Preserves speaker and timestamp metadata.
    """

    def __init__(self):
        # Audio files can be large, set generic limit (e.g. 100MB)
        # Gemini handles larger files, but we enforce safety limits for upload
        super().__init__(max_file_size_bytes=100 * 1024 * 1024)

    async def process(self, file_path: str, ai_provider: Optional[str] = None) -> List[ProcessedDocument]:
        """
        Transcribe audio file and return text segments.
        """
        path = await self._validate_file_path(file_path)

        try:
            # P1: On-demand instantiation to avoid side effects at module import time
            # and to pick up latest environment variables.
            # Create async DB session and SettingsService
            session_factory = get_session_factory()
            async with session_factory() as db:
                settings_service = SettingsService(db)

                # Priority: 1. Passed provider (connector), 2. Global embedding_provider
                provider = ai_provider
                if not provider:
                    provider = await settings_service.get_value("embedding_provider") or "ollama"

                if provider == "gemini":
                    client = await get_gemini_client(settings_service)
                    service = GeminiAudioService(client, settings_service)
                elif provider in ["ollama", "local"]:
                    from app.services.whisper_audio_service import WhisperAudioService

                    service = WhisperAudioService(settings_service)
                else:
                    # Fallback or OpenAI (which could also use WhisperAudioService if configured for cloud)
                    # For now, if not gemini, let's try local Whisper if provider is local-ish
                    from app.services.whisper_audio_service import WhisperAudioService

                    service = WhisperAudioService(settings_service)

                logger.info(f"Audio Processing Started ({provider}): {path.name}")

                # Call Service (delegation)
                chunks = await service.transcribe_file(str(path))

                documents = []
                for i, chunk in enumerate(chunks):
                    # Format text content for RAG
                    formatted_text = f"[{chunk.timestamp_start}] {chunk.speaker}: {chunk.text}"

                    # Metadata
                    meta: DocumentMetadata = {
                        "file_name": path.name,
                        "file_size": path.stat().st_size,
                        "page_number": 1,  # Audio doesn't have pages, use 1
                        "chunk_index": i,
                        "source_type": "audio",
                        # Custom fields (not in TypedDict but allowed by Python dicts)
                        "speaker": chunk.speaker,
                        "timestamp_start": chunk.timestamp_start,
                    }

                    documents.append(ProcessedDocument(content=formatted_text, metadata=meta, success=True))

                logger.info(f"Audio Processing Complete: {path.name} | {len(documents)} segments")
                if not documents:
                    logger.warning(f"Audio Processing Yielded No Content: {path.name}")
                    # Return empty success doc or failure?
                    # Better to return empty list usually, but Pipeline expects something.
                    # If truly empty, maybe it was silent.

                return documents

        except Exception as e:
            logger.error(f"Audio Processing Failed: {path.name} | {e}", exc_info=True)
            return [
                ProcessedDocument(
                    content="",
                    metadata={"file_name": path.name, "source_type": "audio"},
                    success=False,
                    error_message=str(e),
                )
            ]

    def get_supported_extensions(self) -> List[str]:
        return ["mp3", "wav", "m4a", "aac", "flac", "ogg"]
