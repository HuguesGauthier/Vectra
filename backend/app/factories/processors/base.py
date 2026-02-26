"""
File Processor Base - Abstract interface for file ingestion processors.

Defines the contract for processing different file types.
"""

from __future__ import annotations  # PEP 563 - Allows list[T] syntax in Python 3.8

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypedDict


class DocumentMetadata(TypedDict, total=False):
    """
    Typed dictionary for document metadata.

    Common fields across processors:
        - file_name: Original filename
        - file_size: Size in bytes
        - page_number: Page number (for multi-page documents)
        - chunk_index: Chunk index (for chunked documents)
        - source_type: File type (pdf, csv, docx, etc.)
    """

    file_name: str
    file_size: int
    page_number: int
    chunk_index: int
    source_type: str


@dataclass
class ProcessedDocument:
    """
    Result of file processing.

    ARCHITECT NOTE: Data Transfer Object
    Standardizes output across different file processors.

    Attributes:
        content: Extracted text content from the document
        metadata: Additional information about the processed document
        success: Whether the processing was successful
        error_message: Error details if processing failed (required when success=False)
    """

    content: str
    metadata: DocumentMetadata = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None

    def __post_init__(self):
        """
        Validate consistency between success status and error message.

        ARCHITECT NOTE: Defensive Programming
        Prevents inconsistent states at object creation time.
        """
        if not self.success and self.error_message is None:
            raise ValueError("error_message is required when success=False. " "Provide details about what went wrong.")
        if self.success and self.error_message is not None:
            raise ValueError(
                "error_message should be None when success=True. "
                "Successful processing should not have error messages."
            )


class FileProcessor(ABC):
    """
    Abstract base class for file processors.

    ARCHITECT NOTE: Template Method Pattern
    Defines the interface for processing files.
    Each processor handles a specific file type (CSV, PDF, DOCX, etc.).

    Security Considerations:
        - Implementations MUST validate file paths to prevent directory traversal
        - Implementations SHOULD set file size limits to prevent DoS
        - Implementations MUST handle malformed/malicious files gracefully
    """

    def __init__(self, max_file_size_bytes: int = 100 * 1024 * 1024):
        """
        Initialize file processor.

        Args:
            max_file_size_bytes: Maximum allowed file size (default: 100 MB)
        """
        self.max_file_size_bytes = max_file_size_bytes

    @abstractmethod
    async def process(self, file_path: str, ai_provider: Optional[str] = None) -> list[ProcessedDocument]:
        """
        Process a file and extract content.

        Args:
            file_path: Absolute path to the file

        Returns:
            List of processed documents (chunks/pages). Can return multiple
            documents if the file is split into chunks or contains multiple pages.

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            ValueError: If file format is invalid or file too large

        Security Notes:
            - Validate file_path to prevent directory traversal attacks
            - Check file size before processing to prevent memory exhaustion
            - Handle exceptions gracefully and return ProcessedDocument with success=False

        Example:
            >>> processor = PdfProcessor()
            >>> documents = await processor.process("/path/to/file.pdf")
            >>> for doc in documents:
            ...     if doc.success:
            ...         print(doc.content)
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """
        Get list of file extensions this processor supports.

        Returns:
            List of lowercase extensions without dots (e.g., ['csv', 'xlsx'])

        Example:
            >>> processor = PdfProcessor()
            >>> processor.get_supported_extensions()
            ['pdf']
        """
        pass

    async def _validate_file_path(self, file_path: str) -> Path:
        """
        Validate and normalize file path (async, non-blocking).

        Args:
            file_path: Path to validate

        Returns:
            Absolute Path object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is suspicious or file too large

        SECURITY: Prevents directory traversal attacks and DoS

        Example:
            >>> processor = PdfProcessor()
            >>> path = await processor._validate_file_path("document.pdf")
            >>> assert path.exists()
        """

        # Run blocking I/O operations in thread pool to avoid blocking event loop
        def _validate_sync() -> Path:
            path = Path(file_path).resolve()

            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            if not path.is_file():
                raise ValueError(f"Path is not a file: {path}")

            # Security: Check file size to prevent DoS
            file_size = path.stat().st_size
            if file_size > self.max_file_size_bytes:
                raise ValueError(
                    f"File too large: {file_size:,} bytes "
                    f"(maximum allowed: {self.max_file_size_bytes:,} bytes). "
                    "This limit prevents memory exhaustion attacks."
                )

            return path

        # Run in thread pool to avoid blocking the event loop
        return await asyncio.to_thread(_validate_sync)

    def _validate_file_path_within_directory(self, file_path: str, allowed_directory: Path) -> Path:
        """
        Enhanced validation: ensure file is within an allowed directory.

        Args:
            file_path: Path to validate
            allowed_directory: Directory that file must be within

        Returns:
            Validated Path object

        Raises:
            ValueError: If file is outside allowed directory

        SECURITY: Prevents directory traversal by checking resolved paths

        Example:
            >>> processor = PdfProcessor()
            >>> allowed = Path("/var/uploads")
            >>> # This will raise ValueError
            >>> path = processor._validate_file_path_within_directory(
            ...     "/var/uploads/../../etc/passwd",
            ...     allowed
            ... )
        """
        path = Path(file_path).resolve()
        allowed = allowed_directory.resolve()

        # Security: Check if resolved path is within allowed directory
        try:
            path.relative_to(allowed)
        except ValueError:
            raise ValueError(
                f"Security violation: File {path} is outside allowed directory {allowed}. "
                "This prevents directory traversal attacks."
            )

        return path
