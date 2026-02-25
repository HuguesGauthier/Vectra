import logging
import httpx
import os
from typing import List, Optional, Callable
from app.core.exceptions import ExternalDependencyError
from app.services.settings_service import SettingsService
from app.services.gemini_audio_service import TranscriptionChunk

logger = logging.getLogger(__name__)

class WhisperAudioService:
    """
    Local Whisper Audio Service using faster-whisper-server (OpenAI compatible).
    """

    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service

    async def transcribe_file(
        self, file_path: str, callback: Optional[Callable[[str], None]] = None
    ) -> List[TranscriptionChunk]:
        base_url = await self.settings_service.get_value("whisper_base_url")
        if not base_url:
             base_url = "http://vectra-whisper:8000/v1" # Internal docker network default
        
        # If running locally outside docker, it might be localhost:8003
        if "localhost" in base_url and os.environ.get("DOCKER_CONTAINER"):
             base_url = base_url.replace("localhost", "vectra-whisper")

        model_name = await self.settings_service.get_value("ollama_transcription_model") or "base"

        if callback:
            callback(f"Transcribing locally with Whisper ({model_name})...")

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": f}
                    data = {
                        "model": model_name,
                        "response_format": "verbose_json"
                    }
                    response = await client.post(
                        f"{base_url}/audio/transcriptions",
                        files=files,
                        data=data
                    )
                
                response.raise_for_status()
                result = response.json()

                chunks = []
                segments = result.get("segments", [])
                
                for segment in segments:
                    start_sec = int(segment.get("start", 0))
                    timestamp_display = self._format_seconds(start_sec)
                    
                    chunks.append(
                        TranscriptionChunk(
                            timestamp_start=timestamp_display,
                            timestamp_end=self._format_seconds(int(segment.get("end", 0))),
                            speaker="Speaker", 
                            text=segment.get("text", "").strip(),
                            start_seconds=start_sec,
                            timestamp_display=timestamp_display
                        )
                    )
                
                return chunks
        except Exception as e:
            logger.error(f"Whisper transcription failed: {str(e)}", exc_info=True)
            raise ExternalDependencyError(f"Local Whisper transcription failed: {str(e)}")

    def _format_seconds(self, seconds: int) -> str:
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
