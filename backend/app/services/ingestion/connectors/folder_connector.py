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

        # P1: Config-driven filtering
        # Convert glob patterns to extensions if they are simple *.ext,
        # or handle as needed. SimpleDirectoryReader's required_exts
        # is the most efficient way for simple extensions.
        required_exts = None
        if config.patterns and "*" not in config.patterns:
            # If patterns are like [".pdf", ".docx"], SimpleDirectoryReader handles them
            required_exts = [p if p.startswith(".") else f".{p}" for p in config.patterns]

        def _load_sync():
            reader = SimpleDirectoryReader(
                input_dir=config.path, recursive=config.recursive, required_exts=required_exts
            )
            docs = reader.load_data()

            # P0 Fix: Enforce relative paths for cross-platform/portable persistence
            for doc in docs:
                full_path = doc.metadata.get("file_path") or doc.id_
                if full_path and os.path.isabs(full_path):
                    try:
                        rel_path = os.path.relpath(full_path, config.path)
                        doc.metadata["file_path"] = rel_path
                        doc.id_ = rel_path
                    except ValueError:
                        pass
            return docs

        try:
            return await asyncio.to_thread(_load_sync)
        except Exception as e:
            raise RuntimeError(f"Failed to ingest folder {config.path}: {str(e)}") from e
