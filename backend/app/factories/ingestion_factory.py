"""
Ingestion Factory - Maps file extensions to appropriate processors.

Implements the Factory Pattern with thread-safe instance caching.
"""

import logging
import threading
from typing import Dict, Final, List, Type

from app.core.exceptions import ValidationError
from app.factories.processors.archive_processor import ArchiveProcessor
from app.factories.processors.audio_processor import AudioProcessor
from app.factories.processors.base import FileProcessor
from app.factories.processors.csv_processor import CsvProcessor
from app.factories.processors.email_processor import EmailProcessor
from app.factories.processors.image_processor import ImageProcessor
from app.factories.processors.office_processor import OfficeProcessor
from app.factories.processors.pdf_processor import PdfProcessor  # Hybrid with fallback
from app.factories.processors.text_processor import TextProcessor

logger = logging.getLogger(__name__)


class IngestionFactory:
    """
    Thread-safe factory for creating file processors based on file extension.

    ARCHITECT NOTE: Factory Pattern + Singleton Caching
    - Centralizes processor creation logic
    - Caches processor instances for performance
    - Thread-safe for concurrent access

    PDF PROCESSING STRATEGY:
    - Hybrid PdfProcessor with automatic fallback
    - LlamaParse (cloud) → MarkItDown (local) on failure

    OFFICE PROCESSING STRATEGY:
    - OfficeProcessor uses MarkItDown for all formats
    - Supports: .docx, .xlsx, .pptx, .doc

    TEXT PROCESSING STRATEGY:
    - TextProcessor handles plain text, markdown, and code files

    AUDIO PROCESSING STRATEGY:
    - AudioProcessor uses Gemini 1.5 Flash for transcription

    IMAGE PROCESSING STRATEGY:
    - ImageProcessor uses Gemini 1.5 Flash Vision

    EMAIL PROCESSING STRATEGY:
    - EmailProcessor uses standard lib (eml) + extract-msg (msg)
    """

    # Immutable registry of processor classes
    _PROCESSOR_REGISTRY: Final[Dict[str, Type[FileProcessor]]] = {
        # --- OFFICE & DOCS (Le Standard) ---
        "csv": CsvProcessor,
        "pdf": PdfProcessor,
        "doc": OfficeProcessor,
        "docx": OfficeProcessor,
        "xlsx": OfficeProcessor,
        "xls": OfficeProcessor,  # Lean on MarkItDown/OfficeProcessor
        "pptx": OfficeProcessor,
        "ppt": OfficeProcessor,
        # --- CODE & TEXTE ---
        "txt": TextProcessor,
        "md": TextProcessor,
        "markdown": TextProcessor,
        "py": TextProcessor,
        "js": TextProcessor,
        "html": TextProcessor,
        "css": TextProcessor,
        "log": TextProcessor,
        "json": TextProcessor,
        "xml": TextProcessor,
        "yaml": TextProcessor,
        "yml": TextProcessor,
        "sql": TextProcessor,
        # --- IMAGES (OCR - Vision AI) ---
        "jpg": ImageProcessor,
        "jpeg": ImageProcessor,
        "png": ImageProcessor,
        "tiff": ImageProcessor,
        "bmp": ImageProcessor,
        "heic": ImageProcessor,
        # --- EMAILS ---
        "eml": EmailProcessor,
        "msg": EmailProcessor,
        # --- AUDIO (Transcriptions) ---
        "mp3": AudioProcessor,
        "wav": AudioProcessor,
        "m4a": AudioProcessor,
        "aac": AudioProcessor,
        "flac": AudioProcessor,
        "ogg": AudioProcessor,
        # --- ARCHIVES ---
        "zip": ArchiveProcessor,
    }

    # Thread-safe instance cache
    _instances: Dict[Type[FileProcessor], FileProcessor] = {}
    _cache_lock = threading.Lock()

    # Dynamic registration (mutable, protected by lock)
    _dynamic_registry: Dict[str, Type[FileProcessor]] = {}
    _registry_lock = threading.Lock()

    @classmethod
    def get_processor(cls, file_extension: str) -> FileProcessor:
        """
        Get appropriate processor for file extension (thread-safe).

        Args:
            file_extension: File extension (e.g., 'csv', 'pdf')

        Returns:
            Instance of appropriate file processor

        Raises:
            ValidationError: If file type is not supported or extension is empty
        """
        if not file_extension:
            raise ValidationError("File extension cannot be empty", field="file_extension")

        # Normalize extension (remove dot, lowercase)
        extension = file_extension.lower().lstrip(".")

        # Check both static and dynamic registries
        processor_class = cls._PROCESSOR_REGISTRY.get(extension)
        if not processor_class:
            with cls._registry_lock:
                processor_class = cls._dynamic_registry.get(extension)

        if not processor_class:
            supported = cls.get_supported_extensions()
            error_msg = f"Unsupported file type: {extension}. Supported: {', '.join(sorted(supported))}"
            logger.error(error_msg)
            raise ValidationError(
                error_msg, field="file_extension", details={"extension": extension, "supported": supported}
            )

        # Thread-safe instance caching with double-check locking
        if processor_class not in cls._instances:
            with cls._cache_lock:
                # Double-check after acquiring lock
                if processor_class not in cls._instances:
                    logger.info(f"Instantiating new processor: {processor_class.__name__}")
                    cls._instances[processor_class] = processor_class()

        return cls._instances[processor_class]

    @classmethod
    def register_processor(cls, extension: str, processor_class: Type[FileProcessor], override: bool = False) -> None:
        """
        Register a new processor for a file extension (thread-safe).

        ARCHITECT NOTE: Open/Closed Principle
        Allows adding new processors without modifying existing code.

        Args:
            extension: File extension (e.g., 'xlsx')
            processor_class: Processor class to handle this extension
            override: If True, allows replacing an existing registration

        Raises:
            ValueError: If extension already registered and override=False
        """
        ext = extension.lower().lstrip(".")

        with cls._registry_lock:
            # Check if already in static registry
            if ext in cls._PROCESSOR_REGISTRY:
                if not override:
                    raise ValueError(f"Extension '{ext}' is in static registry. Cannot override built-in processor.")
                logger.warning(f"Overriding built-in processor for '{ext}'")

            # Check dynamic registry
            if ext in cls._dynamic_registry and not override:
                raise ValueError(f"Extension '{ext}' already registered. Use override=True to replace.")

            cls._dynamic_registry[ext] = processor_class
            logger.info(f"Registered {processor_class.__name__} for extension: {ext}")

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """
        Get list of all supported file extensions.

        Returns:
            Sorted list of supported extensions (static + dynamic)
        """
        with cls._registry_lock:
            all_extensions = set(cls._PROCESSOR_REGISTRY.keys()) | set(cls._dynamic_registry.keys())
        return sorted(all_extensions)

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the instance cache (thread-safe, useful for testing).
        """
        with cls._cache_lock:
            cls._instances.clear()
        logger.debug("Processor instance cache cleared")

    @classmethod
    def reset_dynamic_registry(cls) -> None:
        """
        Reset dynamic processor registrations (useful for testing).
        """
        with cls._registry_lock:
            cls._dynamic_registry.clear()
        logger.debug("Dynamic processor registry cleared")
