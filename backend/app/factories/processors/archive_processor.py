from __future__ import annotations

import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List

from app.core.exceptions import TechnicalError
from app.factories.processors.base import FileProcessor, ProcessedDocument

logger = logging.getLogger(__name__)


class ArchiveProcessor(FileProcessor):
    """
    Processor for Archives (.zip).
    Extracts contents and delegates to other processors via IngestionFactory.
    """

    # Safety limits
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2GB extracted max (was 500MB)
    MAX_FILE_COUNT = 500  # Max files to process (was 100)

    def __init__(self) -> None:
        # Zip itself can be larger now (500MB upload limit)
        super().__init__(max_file_size_bytes=500 * 1024 * 1024)

    def get_supported_extensions(self) -> List[str]:
        return ["zip"]

    async def process(self, file_path: str) -> List[ProcessedDocument]:
        """
        Extract zip and process contained files.
        """
        zip_path = await self._validate_file_path(file_path)

        # Local import to avoid circular dependency
        from app.factories.ingestion_factory import IngestionFactory

        temp_dir = Path(tempfile.mkdtemp(prefix="vectra_zip_"))
        processed_docs: List[ProcessedDocument] = []

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # 1. Safety Check: total uncompressed size
                total_size = sum(info.file_size for info in zip_ref.infolist())
                if total_size > self.MAX_TOTAL_SIZE:
                    raise TechnicalError(
                        f"Zip extraction limit exceeded. Total size {total_size} > {self.MAX_TOTAL_SIZE}"
                    )

                # 2. Extract
                zip_ref.extractall(temp_dir)

            # 3. Traverse and Delegate
            file_count = 0
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file_count >= self.MAX_FILE_COUNT:
                        logger.warning(
                            f"Zip file count limit reached ({self.MAX_FILE_COUNT}). Skipping remaining files."
                        )
                        break

                    inner_path = Path(root) / file

                    # Skip hidden/system files
                    if file.startswith(".") or file.startswith("__"):
                        continue

                    ext = inner_path.suffix.lower().lstrip(".")
                    if not ext:
                        continue

                    try:
                        # Find processor for this file type
                        processor = IngestionFactory.get_processor(ext)

                        # Process
                        # Note: recursion works automatically if zip contains zip and factory returns ArchiveProcessor
                        docs = await processor.process(str(inner_path))

                        # Enrich metadata to indicate origin
                        for doc in docs:
                            doc.metadata["archive_source"] = zip_path.name
                            doc.metadata["original_filename"] = file
                            # If we want to preserve folder structure:
                            rel_path = inner_path.relative_to(temp_dir)
                            doc.metadata["archive_path"] = str(rel_path)

                        processed_docs.extend(docs)
                        file_count += 1

                    except Exception as e:
                        # Log warning but continue processing other files
                        logger.warning(f"Failed to process file inside zip: {file} | {e}")

        except zipfile.BadZipFile:
            raise TechnicalError(f"Invalid or corrupted zip file: {zip_path.name}")
        except Exception as e:
            logger.error(f"Archive Processing Failed: {zip_path.name} | {e}", exc_info=True)
            raise TechnicalError(f"Failed to process archive: {e}")
        finally:
            # Cleanup temp dir
            shutil.rmtree(temp_dir, ignore_errors=True)

        return processed_docs
