"""
Tests for Text processor.
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.factories.processors.text_processor import TextProcessor


class TestTextProcessorBasics:
    """Basic functionality tests."""

    @pytest.mark.asyncio
    async def test_get_supported_extensions(self):
        """Should support common text and code extensions."""
        processor = TextProcessor()
        extensions = processor.get_supported_extensions()
        assert "txt" in extensions
        assert "md" in extensions
        assert "py" in extensions

    @pytest.mark.asyncio
    async def test_process_simple_text(self):
        """Should correctly read a simple text file."""
        content = "Hello, this is a test text file."
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            processor = TextProcessor()
            results = await processor.process(tmp_path)

            assert len(results) == 1
            doc = results[0]
            assert doc.success is True
            assert doc.content == content
            assert doc.metadata["encoding_used"] == "utf-8"
        finally:
            os.unlink(tmp_path)


class TestTextProcessorFailures:
    """Failure path tests."""

    @pytest.mark.asyncio
    async def test_process_nonexistent_file_returns_error(self):
        """Non-existent file should return error document."""
        processor = TextProcessor()
        results = await processor.process("/nonexistent/file.txt")

        doc = results[0]
        assert doc.success is False
        assert "not found" in doc.error_message.lower()

    @pytest.mark.asyncio
    async def test_process_file_too_large_fails(self):
        """File exceeding size limit should return error document."""
        # Create 30MB file (exceeds 25MB limit)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp.seek(30 * 1024 * 1024)
            tmp.write("x")
            tmp_path = tmp.name

        try:
            processor = TextProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is False
            assert "too large" in doc.error_message.lower()
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_encoding_fallback(self):
        """Should fallback to latin-1 if utf-8 fails."""
        # Content that is valid latin-1 but not valid utf-8
        content_bytes = b"Hello \xe9 (accented e)"
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as tmp:
            tmp.write(content_bytes)
            tmp_path = tmp.name

        try:
            processor = TextProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is True
            assert doc.metadata["encoding_used"] == "latin-1"
            assert "é" in doc.content
        finally:
            os.unlink(tmp_path)
