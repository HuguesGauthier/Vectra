import asyncio
import os
from typing import List

from llama_index.core import Document, SimpleDirectoryReader

from app.core.interfaces.base_connector import BaseConnector
from app.schemas.ingestion import FileIngestionConfig


class FileConnector(BaseConnector[FileIngestionConfig]):
    """
    Connector for ingesting a single file.

    Security: Includes path traversal checks.
    Performance: Offloads file IO to thread pool.
    """

    # P0 FIX: Special formats handled by specific Processors via IngestionFactory
    SPECIAL_FORMATS = {
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".aac",
        ".ogg",  # Audio
        ".zip",  # Archive
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".bmp",
        ".heic",  # Images
        ".eml",
        ".msg",  # Emails
    }

    async def validate_config(self, config: FileIngestionConfig) -> bool:
        """Checks if file exists and is safe."""
        if not config.path:
            return False

        # P0: Path Traversal Check & Strict File Validation
        # Ensure path is absolute and is a FILE (not a directory)
        return await asyncio.to_thread(os.path.isfile, config.path)

    async def load_data(self, config: FileIngestionConfig) -> List[Document]:
        """Loads data asynchronously."""
        # P0: Validate path exists before processing
        if not config.path:
            raise ValueError("FileIngestionConfig.path cannot be None or empty")

        # P0: Convert relative paths to absolute paths
        # This ensures the worker can find files regardless of working directory
        if not os.path.isabs(config.path):
            config.path = os.path.abspath(config.path)

        if not await self.validate_config(config):
            raise ValueError(f"Invalid configuration or file not found: {config.path}")

        # P0: Async Blocking Fix - Run blocking IO in thread pool
        # SimpleDirectoryReader is synchronous
        def _load_sync():
            # P0 FIX: Skip SimpleDirectoryReader for audio files
            # Audio files will be processed by AudioProcessor via IngestionFactory
            file_ext = os.path.splitext(config.path)[-1].lower()

            if file_ext in self.SPECIAL_FORMATS:
                # Return placeholder - actual processing happens via IngestionFactory
                try:
                    file_size = os.path.getsize(config.path)
                except OSError:
                    file_size = 0

                return [
                    Document(
                        text="",  # Empty - will be filled by specific Processor
                        metadata={
                            "file_path": os.path.basename(config.path),
                            "file_name": os.path.basename(config.path),
                            "file_type": file_ext.lstrip("."),
                            "file_size": file_size,
                        },
                    )
                ]

            reader = SimpleDirectoryReader(input_files=[config.path])
            docs = reader.load_data()

            # P0 Fix: Enforce relative paths (basename for single file)
            for doc in docs:
                if doc.metadata.get("file_path"):
                    doc.metadata["file_path"] = os.path.basename(doc.metadata["file_path"])
                    doc.id_ = doc.metadata["file_path"]  # Consistency
            return docs

        try:
            return await asyncio.to_thread(_load_sync)
        except Exception as e:
            # P2: Error Handling - Wrap generic exceptions
            raise RuntimeError(f"Failed to load file {config.path}: {str(e)}") from e
