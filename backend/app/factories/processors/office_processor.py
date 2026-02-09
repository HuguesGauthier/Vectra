"""
Office Processor - Handles all Office documents (.docx, .xlsx, .pptx, .doc).

SECURITY HARDENED: Production-ready with PII protection, DoS mitigation, singleton caching.
USES: MarkItDown library for all Office formats (no API key required)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
from pathlib import Path
from typing import Final, Optional

from pydantic import BaseModel, Field

from app.core.exceptions import TechnicalError
from app.core.settings import get_settings
from app.factories.processors.base import (DocumentMetadata, FileProcessor,
                                           ProcessedDocument)

logger = logging.getLogger(__name__)


# ========== CUSTOM EXCEPTIONS (P2) ==========
class OfficeError(TechnicalError):
    """Base exception for Office processing errors."""

    pass


class OfficeParseError(OfficeError):
    """Raised when MarkItDown fails to parse a document."""

    pass


class OfficeLibraryNotInstalledError(OfficeError):
    """Raised when MarkItDown library is not available."""

    pass


# ========== TYPED METADATA (P2) ==========
class OfficeFileMetadata(BaseModel):
    """Strongly typed metadata for Office files."""

    file_type: str = "office"
    file_name_hash: str  # SHA256 of filename for audit trails (P0: No PII)
    file_extension: str
    char_count: int = Field(ge=0)
    source_tool: str = "MarkItDown"
    truncated: bool = False


# ========== PROCESSOR CLASS ==========
class OfficeProcessor(FileProcessor):
    """
    Office document processor using MarkItDown library.

    SUPPORTS: .docx, .xlsx, .pptx, .doc

    SECURITY HARDENED:
    - PII Protection: Filenames hashed before logging
    - DoS Mitigation: Content size limits + timeout
    - Singleton Pattern: MarkItDown instance reused (thread-safe)
    - Type Safety: Pydantic models for metadata
    """

    # Configuration (P2: Inject from settings)
    _settings = get_settings()
    MAX_FILE_SIZE_MB: Final[int] = 50
    PARSE_TIMEOUT_SECONDS: Final[float] = 60.0
    MAX_CONTENT_SIZE_CHARS: Final[int] = 10_000_000  # 10M chars (~20MB text)

    # Singleton MarkItDown instance (P1: Performance)
    _markitdown_instance: Optional[object] = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self):
        """Initialize processor with inherited file size validation."""
        super().__init__(max_file_size_bytes=self.MAX_FILE_SIZE_MB * 1024 * 1024)

    async def process(self, file_path: Path | str) -> list[ProcessedDocument]:
        """
        Process Office document with full security hardening.

        Returns:
            List with single ProcessedDocument
        """
        file_hash: Optional[str] = None  # For logging

        try:
            # Validate file (async, inherited from base)
            validated_path = await self._validate_file_path(file_path)

            # P0: Hash filename for secure logging (no PII leakage)
            file_hash = self._hash_filename(validated_path.name)
            file_extension = validated_path.suffix.lower()

            logger.info(
                "office_file_processing_started",
                extra={"file_hash": file_hash, "extension": file_extension, "processor": "MarkItDown"},
            )

            # Parse with timeout + content size protection
            content, metadata_dict = await asyncio.wait_for(
                self._parse_office_file(str(validated_path)), timeout=self.PARSE_TIMEOUT_SECONDS
            )

            # P1: Enforce content size limit (DoS protection)
            truncated = False
            if len(content) > self.MAX_CONTENT_SIZE_CHARS:
                logger.warning(
                    "office_file_content_truncated",
                    extra={
                        "file_hash": file_hash,
                        "original_size": len(content),
                        "max_size": self.MAX_CONTENT_SIZE_CHARS,
                    },
                )
                content = content[: self.MAX_CONTENT_SIZE_CHARS]
                truncated = True

            # P2: Type-safe metadata with Pydantic
            office_metadata = OfficeFileMetadata(
                file_name_hash=file_hash, file_extension=file_extension, char_count=len(content), truncated=truncated
            )

            logger.info(
                "office_file_processing_completed",
                extra={"file_hash": file_hash, "char_count": len(content), "truncated": truncated},
            )

            return [
                ProcessedDocument(
                    content=content, metadata=office_metadata.model_dump(), success=True  # Convert to dict
                )
            ]

        except asyncio.TimeoutError:
            logger.error(
                "office_file_processing_timeout",
                extra={"file_hash": file_hash, "timeout_seconds": self.PARSE_TIMEOUT_SECONDS},
            )
            return self._create_error_document("Processing timed out")

        except FileNotFoundError:
            logger.error("office_file_not_found", extra={"file_hash": file_hash})
            return self._create_error_document("File not found")

        except ValueError as e:
            logger.error("office_file_validation_error", extra={"file_hash": file_hash, "error": str(e)})
            return self._create_error_document(f"Validation failed: {str(e)}")

        except OfficeError as e:
            logger.error("office_processing_error", extra={"file_hash": file_hash, "error": str(e)}, exc_info=True)
            return self._create_error_document(f"Office processing error: {str(e)}")

        except Exception as e:
            logger.error("office_file_unexpected_error", extra={"file_hash": file_hash}, exc_info=True)
            return self._create_error_document(f"Unexpected error: {str(e)}")

    async def _parse_office_file(self, file_path: str) -> tuple[str, dict]:
        """
        Parse Office file in thread pool with singleton MarkItDown instance.

        Returns:
            (content_text, metadata_dict)
        """
        result = await asyncio.to_thread(self._sync_parse_office, file_path)

        content = result["text_content"]
        metadata = {"file_type": "office", "char_count": len(content)}

        return content, metadata

    def _sync_parse_office(self, file_path: str) -> dict:
        """
        Synchronous parsing with singleton MarkItDown (P1: Performance).

        Raises:
            DocxLibraryNotInstalledError: If library missing
            DocxParseError: If parsing fails
        """
        try:
            # P1: Use singleton instance (thread-safe lazy init)
            md_instance = self._get_markitdown_instance()
            result = md_instance.convert(file_path)

            return {"text_content": result.text_content, "file_type": "office"}

        except ImportError as e:
            raise OfficeLibraryNotInstalledError(
                "MarkItDown library not installed. Install: pip install markitdown"
            ) from e

        except Exception as e:
            raise OfficeParseError(f"Failed to parse Office file: {e}") from e

    @classmethod
    def _get_markitdown_instance(cls) -> object:
        """
        Get singleton MarkItDown instance (P1: Performance + Thread-Safe).

        Uses double-checked locking pattern for efficiency.
        """
        if cls._markitdown_instance is not None:
            return cls._markitdown_instance

        with cls._instance_lock:
            # Double-check after acquiring lock
            if cls._markitdown_instance is None:
                from markitdown import MarkItDown

                cls._markitdown_instance = MarkItDown()
                logger.info("markitdown_instance_initialized")

            return cls._markitdown_instance

    @staticmethod
    def _hash_filename(filename: str) -> str:
        """
        Hash filename for secure logging (P0: PII Protection).

        Returns SHA256 hash prefix for audit trails.
        """
        return hashlib.sha256(filename.encode()).hexdigest()[:16]

    @staticmethod
    def _create_error_document(error_msg: str) -> list[ProcessedDocument]:
        """Helper to create standardized error response."""
        return [ProcessedDocument(content="", metadata={"file_type": "office"}, success=False, error_message=error_msg)]

    def get_supported_extensions(self) -> list[str]:
        """Supported Office formats."""
        return ["docx", "xlsx", "pptx", "doc"]
