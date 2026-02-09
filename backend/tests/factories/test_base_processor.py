"""
Comprehensive tests for FileProcessor base class with async validation.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.factories.processors.base import (DocumentMetadata, FileProcessor,
                                           ProcessedDocument)


class TestProcessedDocument:
    """Tests for ProcessedDocument dataclass."""

    def test_successful_document_creation(self):
        """Success=True should not require error_message."""
        doc = ProcessedDocument(content="Test content", success=True)
        assert doc.success is True
        assert doc.error_message is None

    def test_failed_document_requires_error_message(self):
        """Success=False must have error_message."""
        doc = ProcessedDocument(content="", success=False, error_message="File corrupted")
        assert doc.success is False
        assert doc.error_message == "File corrupted"

    def test_failed_document_without_error_message_raises(self):
        """Success=False without error_message should raise."""
        with pytest.raises(ValueError) as exc_info:
            ProcessedDocument(content="", success=False, error_message=None)
        assert "error_message is required" in str(exc_info.value)

    def test_successful_document_with_error_message_raises(self):
        """Success=True with error_message should raise."""
        with pytest.raises(ValueError) as exc_info:
            ProcessedDocument(content="Test", success=True, error_message="Should not have error")
        assert "should be None when success=True" in str(exc_info.value)

    def test_metadata_typing(self):
        """Metadata should accept typed dict."""
        metadata: DocumentMetadata = {"file_name": "test.pdf", "file_size": 1024, "page_number": 1}
        doc = ProcessedDocument(content="Test", metadata=metadata)
        assert doc.metadata["file_name"] == "test.pdf"


class ConcreteProcessor(FileProcessor):
    """Concrete implementation for testing."""

    async def process(self, file_path: str) -> list[ProcessedDocument]:
        path = await self._validate_file_path(file_path)
        return [ProcessedDocument(content=f"Processed: {path.name}")]

    def get_supported_extensions(self) -> list[str]:
        return ["test"]


class TestFileProcessorValidation:
    """Tests for async file path validation."""

    @pytest.mark.asyncio
    async def test_validate_existing_file_success(self):
        """Valid file should pass validation."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            processor = ConcreteProcessor()
            validated_path = await processor._validate_file_path(tmp_path)
            assert validated_path.exists()
            assert validated_path.is_file()
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_validate_nonexistent_file_fails(self):
        """Non-existent file should raise FileNotFoundError."""
        processor = ConcreteProcessor()

        with pytest.raises(FileNotFoundError) as exc_info:
            await processor._validate_file_path("/nonexistent/file.test")
        assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_directory_fails(self):
        """Directory path should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = ConcreteProcessor()

            with pytest.raises(ValueError) as exc_info:
                await processor._validate_file_path(tmpdir)
            assert "not a file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_too_large_fails(self):
        """File exceeding size limit should raise ValueError."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as tmp:
            # Write 2 MB of data
            tmp.write(b"x" * (2 * 1024 * 1024))
            tmp_path = tmp.name

        try:
            # Set max size to 1 MB
            processor = ConcreteProcessor(max_file_size_bytes=1024 * 1024)

            with pytest.raises(ValueError) as exc_info:
                await processor._validate_file_path(tmp_path)
            assert "too large" in str(exc_info.value)
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_validate_runs_in_thread_pool(self):
        """Validation should use thread pool to avoid blocking."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            processor = ConcreteProcessor()

            # Mock asyncio.to_thread to verify it's called
            with patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread:
                await processor._validate_file_path(tmp_path)
                # Verify thread pool was used
                assert mock_to_thread.called
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_custom_max_file_size(self):
        """Instance should respect custom max file size."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".test") as tmp:
            tmp.write(b"x" * 500)
            tmp_path = tmp.name

        try:
            # Create processor with 100 byte limit
            processor = ConcreteProcessor(max_file_size_bytes=100)

            with pytest.raises(ValueError) as exc_info:
                await processor._validate_file_path(tmp_path)
            assert "too large" in str(exc_info.value)
        finally:
            os.unlink(tmp_path)


class TestDirectoryConfinementValidation:
    """Tests for enhanced directory confinement validation."""

    def test_validate_file_within_directory_success(self):
        """File within allowed directory should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file in allowed directory
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")

            processor = ConcreteProcessor()
            validated = processor._validate_file_path_within_directory(str(test_file), Path(tmpdir))
            assert validated == test_file.resolve()

    def test_validate_file_outside_directory_fails(self):
        """File outside allowed directory should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed = Path(tmpdir)
            outside_file = Path(tmpdir).parent / "outside.txt"

            processor = ConcreteProcessor()

            with pytest.raises(ValueError) as exc_info:
                processor._validate_file_path_within_directory(str(outside_file), allowed)
            assert "Security violation" in str(exc_info.value)
            assert "outside allowed directory" in str(exc_info.value)

    def test_validate_prevents_directory_traversal(self):
        """Directory traversal attempts should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed = Path(tmpdir) / "uploads"
            allowed.mkdir()

            # Create a file in the parent directory
            parent_file = Path(tmpdir) / "secret.txt"
            parent_file.write_text("secret")

            processor = ConcreteProcessor()

            # Try to access parent directory via traversal
            traversal_path = str(allowed / ".." / "secret.txt")

            with pytest.raises(ValueError) as exc_info:
                processor._validate_file_path_within_directory(traversal_path, allowed)
            assert "Security violation" in str(exc_info.value)
