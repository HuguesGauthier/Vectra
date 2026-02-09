"""
Tests for Office processor.
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.factories.processors.office_processor import OfficeProcessor


class TestOfficeProcessorBasics:
    """Basic functionality tests."""

    @pytest.mark.asyncio
    async def test_get_supported_extensions(self):
        """Should support all common office extensions."""
        processor = OfficeProcessor()
        extensions = processor.get_supported_extensions()
        assert "docx" in extensions
        assert "xlsx" in extensions
        assert "pptx" in extensions
        assert "doc" in extensions

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Processor should initialize with correct file size limit."""
        processor = OfficeProcessor()
        # The new processor uses 50MB limit from settings
        assert processor.max_file_size_bytes == 50 * 1024 * 1024


class TestOfficeProcessorFailures:
    """Failure path tests."""

    @pytest.mark.asyncio
    async def test_process_nonexistent_file_returns_error(self):
        """Non-existent file should return error document instead of raising."""
        processor = OfficeProcessor()
        results = await processor.process("/nonexistent/file.docx")

        doc = results[0]
        assert doc.success is False
        assert "not found" in doc.error_message.lower()

    @pytest.mark.asyncio
    async def test_process_invalid_docx_fails_gracefully(self):
        """Invalid DOCX file should return error document."""
        # Create a fake "DOCX" (just text file with .docx extension)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".docx") as tmp:
            tmp.write("This is not a valid DOCX file")
            tmp_path = tmp.name

        try:
            processor = OfficeProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is False
            # MarkItDown might report "Office processing error"
            assert doc.metadata["file_type"] == "office"
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_process_file_too_large_fails(self):
        """File exceeding size limit should return error document."""
        # Create 60MB file (exceeds 50MB limit)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".docx") as tmp:
            tmp.seek(60 * 1024 * 1024)
            tmp.write("x")
            tmp_path = tmp.name

        try:
            processor = OfficeProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is False
            assert "too large" in doc.error_message.lower()
        finally:
            os.unlink(tmp_path)
