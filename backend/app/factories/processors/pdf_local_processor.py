"""
PDF Local Processor - Powered by pypdf.

REPLACES: MarkItDown / Docling
WHY: Lightweight, fast, valid metadata extraction.
TYPE: Local Inference (CPU) - No API Key required.

SECURITY: Path sanitization, content size limits
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Final, Optional

import pypdf
from pydantic import BaseModel, Field

from app.core.exceptions import TechnicalError
from app.factories.processors.base import FileProcessor, ProcessedDocument

logger = logging.getLogger(__name__)


# ========== TYPED METADATA ==========
class PdfLocalMetadata(BaseModel):
    """Metadata extraction enriched by pypdf."""

    file_type: str = "pdf"
    file_name_hash: str
    page_count: int = Field(ge=0)
    source_tool: str = "pypdf (Local)"
    has_tables: bool = False  # pypdf doesn't detect tables reliably
    has_images: bool = False  # If True, indicates document is not "100% text"
    processing_time_ms: float = 0.0
    content_size_bytes: int = Field(ge=0)
    truncated: bool = False


# ========== PROCESSOR CLASS ==========
class PdfLocalProcessor(FileProcessor):
    """
    Lightweight local PDF processor using pypdf.

    PERFORMANCE NOTE:
    Fast CPU-bound processing, no machine learning models required.

    SECURITY:
    - No PII in logs (hashed filenames only)
    - Content size limits enforcement
    """

    # Configuration constants
    MAX_FILE_SIZE_MB: Final[int] = 100
    MAX_CONTENT_SIZE_MB: Final[int] = 50  # Prevent OOM

    def __init__(self):
        super().__init__(max_file_size_bytes=self.MAX_FILE_SIZE_MB * 1024 * 1024)

    async def process(self, file_path: str, ai_provider: Optional[str] = None) -> List[ProcessedDocument]:
        """
        Process PDF using pypdf.
        executes CPU-bound pypdf logic in a thread/executor to avoid blocking the event loop (P0 fix).
        Returns one ProcessedDocument PER PAGE to preserve page numbers.
        """
        file_hash: Optional[str] = None

        try:
            # 1. Validation & Setup (Async)
            validated_path = await self._validate_file_path(file_path)
            file_hash = self._hash_filename(validated_path.name)

            logger.info("pdf_local_pypdf_start", extra={"file_hash": file_hash})

            # 2. Define Blocking Logic (CPU Bound)
            def _process_sync() -> list[ProcessedDocument]:
                start_time = time.time()
                reader = pypdf.PdfReader(str(validated_path))
                page_count = len(reader.pages)
                results_inner = []

                if page_count > 0:
                    for page_idx, page in enumerate(reader.pages, start=1):
                        try:
                            page_content = page.extract_text()

                            if not page_content or not page_content.strip():
                                continue

                            # Metadata calculation
                            content_bytes = len(page_content.encode("utf-8"))
                            truncated = False

                            # Truncate if needed
                            max_bytes = self.MAX_CONTENT_SIZE_MB * 1024 * 1024
                            if content_bytes > max_bytes:
                                page_bytes = page_content.encode("utf-8")[:max_bytes]
                                page_content = page_bytes.decode("utf-8", errors="ignore")
                                truncated = True

                            # Check for images (Not 100% text)
                            has_images = False
                            try:
                                if hasattr(page, "images") and len(page.images) > 0:
                                    has_images = True
                            except Exception:
                                # Fallback if image extraction fails (safe default)
                                pass

                            duration = (time.time() - start_time) * 1000

                            page_metadata = PdfLocalMetadata(
                                file_name_hash=file_hash,
                                page_count=page_count,
                                has_tables=False,
                                has_images=has_images,
                                processing_time_ms=duration,
                                content_size_bytes=len(page_content.encode("utf-8")),
                                truncated=truncated,
                            ).model_dump()

                            page_metadata["page_number"] = page_idx
                            page_metadata["file_path"] = str(validated_path)

                            results_inner.append(
                                ProcessedDocument(content=page_content, metadata=page_metadata, success=True)
                            )
                        except Exception:
                            continue
                return results_inner

            # 3. Offload to Thread Pool
            results = await asyncio.to_thread(_process_sync)

            if results:
                logger.info(
                    "pdf_local_pypdf_success",
                    extra={
                        "file_hash": file_hash,
                        "processed_pages": len(results),
                    },
                )
                return results
            else:
                logger.error("No pages could be processed or empty document")
                return self._create_error("Failed to extract content from any pages or document empty")

        except Exception as e:
            logger.error("pdf_pypdf_failed", extra={"file_hash": file_hash, "error": str(e)}, exc_info=True)
            return self._create_error(f"pypdf error: {str(e)}")

    @staticmethod
    def _hash_filename(filename: str) -> str:
        """SHA256 hash for secure logging (no PII)."""
        return hashlib.sha256(filename.encode()).hexdigest()[:16]

    @staticmethod
    def _create_error(msg: str) -> list[ProcessedDocument]:
        return [ProcessedDocument(content="", metadata={}, success=False, error_message=msg)]

    def get_supported_extensions(self) -> list[str]:
        return ["pdf"]
