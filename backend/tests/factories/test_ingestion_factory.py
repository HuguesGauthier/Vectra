"""
Comprehensive tests for the thread-safe IngestionFactory.
"""

import threading
from unittest.mock import Mock

import pytest

from app.core.exceptions import ValidationError
from app.factories.ingestion_factory import IngestionFactory
from app.factories.processors.base import FileProcessor


class TestIngestionFactoryThreadSafety:
    """Thread-safety tests for concurrent processor access."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset factory state before each test."""
        IngestionFactory.clear_cache()
        IngestionFactory.reset_dynamic_registry()
        yield
        IngestionFactory.clear_cache()
        IngestionFactory.reset_dynamic_registry()

    def test_concurrent_get_processor_thread_safety(self):
        """Verify only one instance is created under high concurrency."""
        results = []
        barrier = threading.Barrier(20)  # Synchronize 20 threads

        def concurrent_access():
            barrier.wait()  # All threads start simultaneously
            processor = IngestionFactory.get_processor("csv")
            results.append(id(processor))

        threads = [threading.Thread(target=concurrent_access) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 20 threads should get the same instance
        assert len(set(results)) == 1, "Multiple instances created under concurrency"

    def test_concurrent_registration_and_access(self):
        """Verify thread-safety when registering and accessing processors."""

        class CustomProcessor(FileProcessor):
            async def process(self, file_path: str):
                return []

            def get_supported_extensions(self) -> list[str]:
                return ["custom"]

        registration_count = {"success": 0, "error": 0}
        lock = threading.Lock()

        def register_and_access():
            try:
                IngestionFactory.register_processor("custom", CustomProcessor, override=True)
                with lock:
                    registration_count["success"] += 1
                processor = IngestionFactory.get_processor("custom")
                assert processor is not None
            except ValueError:
                with lock:
                    registration_count["error"] += 1

        threads = [threading.Thread(target=register_and_access) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should be able to get the custom processor
        processor = IngestionFactory.get_processor("custom")
        assert isinstance(processor, CustomProcessor)


class TestIngestionFactoryValidation:
    """Validation and error handling tests."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        IngestionFactory.clear_cache()
        IngestionFactory.reset_dynamic_registry()
        yield

    def test_get_processor_success_categories(self):
        """Verify key file categories return correct processor types."""
        # PDF Category
        from app.factories.processors.pdf_processor import PdfProcessor

        assert isinstance(IngestionFactory.get_processor("pdf"), PdfProcessor)

        # Office Category
        from app.factories.processors.office_processor import OfficeProcessor

        assert isinstance(IngestionFactory.get_processor("docx"), OfficeProcessor)
        assert isinstance(IngestionFactory.get_processor("xlsx"), OfficeProcessor)

        # Image Category
        from app.factories.processors.image_processor import ImageProcessor

        assert isinstance(IngestionFactory.get_processor("png"), ImageProcessor)

        # Audio Category
        from app.factories.processors.audio_processor import AudioProcessor

        assert isinstance(IngestionFactory.get_processor("mp3"), AudioProcessor)

        # Text Category
        from app.factories.processors.text_processor import TextProcessor

        assert isinstance(IngestionFactory.get_processor("md"), TextProcessor)

    def test_get_processor_empty_extension_fails(self):
        """Empty extension should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IngestionFactory.get_processor("")
        assert "cannot be empty" in str(exc_info.value)

    def test_get_processor_unsupported_extension_fails(self):
        """Unsupported extension should raise ValidationError with details."""
        with pytest.raises(ValidationError) as exc_info:
            IngestionFactory.get_processor("unknown")

        error = exc_info.value
        assert "Unsupported file type" in str(error)
        assert "unknown" in str(error)
        assert error.details is not None
        assert "extension" in error.details

    def test_register_processor_duplicate_without_override_fails(self):
        """Registering duplicate extension without override should fail."""

        class CustomProcessor(FileProcessor):
            async def process(self, file_path: str):
                return []

            def get_supported_extensions(self) -> list[str]:
                return ["custom"]

        IngestionFactory.register_processor("custom", CustomProcessor)

        with pytest.raises(ValueError) as exc_info:
            IngestionFactory.register_processor("custom", CustomProcessor, override=False)
        assert "already registered" in str(exc_info.value)

    def test_register_processor_with_override_succeeds(self):
        """Registering with override=True should replace existing."""

        class CustomProcessor1(FileProcessor):
            async def process(self, file_path: str):
                return []

            def get_supported_extensions(self) -> list[str]:
                return ["custom"]

        class CustomProcessor2(FileProcessor):
            async def process(self, file_path: str):
                return []

            def get_supported_extensions(self) -> list[str]:
                return ["custom"]

        IngestionFactory.register_processor("custom", CustomProcessor1)
        IngestionFactory.register_processor("custom", CustomProcessor2, override=True)

        processor = IngestionFactory.get_processor("custom")
        assert isinstance(processor, CustomProcessor2)

    def test_extension_normalization(self):
        """Extensions should be normalized (lowercase, no dot)."""
        processor1 = IngestionFactory.get_processor("CSV")
        processor2 = IngestionFactory.get_processor(".csv")
        processor3 = IngestionFactory.get_processor("csv")

        # All should return the same instance
        assert processor1 is processor2 is processor3

    def test_static_registry_cannot_be_overridden_without_flag(self):
        """Built-in processors should be protected from accidental override."""

        class CustomProcessor(FileProcessor):
            async def process(self, file_path: str):
                return []

            def get_supported_extensions(self) -> list[str]:
                return ["csv"]

        with pytest.raises(ValueError) as exc_info:
            IngestionFactory.register_processor("csv", CustomProcessor, override=False)
        assert "static registry" in str(exc_info.value)

    def test_get_supported_extensions_includes_all(self):
        """Should return both static and dynamic extensions."""

        class CustomProcessor(FileProcessor):
            async def process(self, file_path: str):
                return []

            def get_supported_extensions(self) -> list[str]:
                return ["custom_ext"]

        # Before registration
        extensions_before = IngestionFactory.get_supported_extensions()
        assert "csv" in extensions_before
        assert "pdf" in extensions_before
        assert "custom_ext" not in extensions_before

        # After registration
        IngestionFactory.register_processor("custom_ext", CustomProcessor)
        extensions_after = IngestionFactory.get_supported_extensions()
        assert "custom_ext" in extensions_after
        assert "csv" in extensions_after
