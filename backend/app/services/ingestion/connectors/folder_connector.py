import asyncio
import os
from typing import List

from llama_index.core import Document, SimpleDirectoryReader

from app.core.interfaces.base_connector import BaseConnector
from app.schemas.ingestion import FolderIngestionConfig


class FolderConnector(BaseConnector[FolderIngestionConfig]):
    """
    Connector for ingesting a folder.

    Security: Checks for valid directory.
    Performance: Offloads recursive scan to thread pool.
    """

    async def validate_config(self, config: FolderIngestionConfig) -> bool:
        if not config.path:
            return False
        return await asyncio.to_thread(os.path.isdir, config.path)

    async def load_data(self, config: FolderIngestionConfig) -> List[Document]:
        if not await self.validate_config(config):
            raise ValueError(f"Invalid configuration or folder not found: {config.path}")

        # P0: Async Blocking Fix
        def _load_sync():
            reader = SimpleDirectoryReader(
                input_dir=config.path,
                recursive=config.recursive,
                # required_exts=None # P0: Config handles filtering via patterns, or defaults to all.
            )
            docs = reader.load_data()

            # P0 Fix: Enforce relative paths
            for doc in docs:
                # LlamaIndex might put absolute path in doc.id_ or metadata
                full_path = doc.metadata.get("file_path") or doc.id_
                if full_path and os.path.isabs(full_path):
                    # Make relative to config.path
                    try:
                        rel_path = os.path.relpath(full_path, config.path)
                        doc.metadata["file_path"] = rel_path
                        doc.id_ = rel_path  # Use relative path as ID for consistency
                    except ValueError:
                        # Path is not relative to root (edge case), keep as is or log warning
                        pass
            return docs

        try:
            return await asyncio.to_thread(_load_sync)
        except Exception as e:
            raise RuntimeError(f"Failed to ingest folder {config.path}: {str(e)}") from e
