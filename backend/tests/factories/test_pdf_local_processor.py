"""
Tests for PDF Local Processor (pypdf version).
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.factories.processors.pdf_local_processor import PdfLocalProcessor


@pytest.fixture
def processor():
    return PdfLocalProcessor()


@pytest.mark.asyncio
class TestPdfLocalProcessor:

    async def test_supported_extensions(self, processor):
        assert processor.get_supported_extensions() == ["pdf"]

    async def test_process_valid_pdf_mocked(self, processor):
        """Test processing with mocked pypdf."""
        # Create a real temp file so _validate_file_path passes
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"content")
            tmp_path = tmp.name

        try:
            with patch("app.factories.processors.pdf_local_processor.pypdf.PdfReader") as mock_reader_cls:
                # Setup mock
                mock_reader = Mock()
                mock_page1 = Mock()
                mock_page1.extract_text.return_value = "Page 1 content"
                mock_page2 = Mock()
                mock_page2.extract_text.return_value = "Page 2 content"

                mock_reader.pages = [mock_page1, mock_page2]
                mock_reader_cls.return_value = mock_reader

                # Process
                results = await processor.process(tmp_path)

                # Verify
                assert len(results) == 2
                assert results[0].content == "Page 1 content"
                assert results[0].metadata["page_number"] == 1
                assert results[0].metadata["page_count"] == 2
                assert results[0].metadata["file_path"] == tmp_path
                assert results[0].success is True

                assert results[1].content == "Page 2 content"
                assert results[1].metadata["page_number"] == 2
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def test_process_empty_page_skip(self, processor):
        """Test that empty pages are skipped."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"content")
            tmp_path = tmp.name

        try:
            with patch("app.factories.processors.pdf_local_processor.pypdf.PdfReader") as mock_reader_cls:
                mock_reader = Mock()
                mock_page1 = Mock()
                mock_page1.extract_text.return_value = "   "  # Empty/whitespace
                mock_page2 = Mock()
                mock_page2.extract_text.return_value = "Real content"

                mock_reader.pages = [mock_page1, mock_page2]
                mock_reader_cls.return_value = mock_reader

                results = await processor.process(tmp_path)

                assert len(results) == 1
                assert results[0].content == "Real content"
                assert results[0].metadata["page_number"] == 2
        finally:
            os.unlink(tmp_path)

    async def test_process_error_handling(self, processor):
        """Test generic error handling during processing."""
        # Use a non-existent file or corrupted file pattern
        # Here we mock invalid file via pypdf raising exception

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"content")
            tmp_path = tmp.name

        try:
            with patch("app.factories.processors.pdf_local_processor.pypdf.PdfReader") as mock_reader_cls:
                mock_reader_cls.side_effect = Exception("Corrupt PDF")

                results = await processor.process(tmp_path)

                assert len(results) == 1
                assert results[0].success is False
                assert "pypdf error: Corrupt PDF" in results[0].error_message
        finally:
            os.unlink(tmp_path)

    async def test_individual_page_failure(self, processor):
        """Test that failure on one page doesn't stop others."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"content")
            tmp_path = tmp.name

        try:
            with patch("app.factories.processors.pdf_local_processor.pypdf.PdfReader") as mock_reader_cls:
                mock_reader = Mock()
                mock_page1 = Mock()
                mock_page1.extract_text.side_effect = Exception("Page error")
                mock_page2 = Mock()
                mock_page2.extract_text.return_value = "Success"

                mock_reader.pages = [mock_page1, mock_page2]
                mock_reader_cls.return_value = mock_reader

                results = await processor.process(tmp_path)

                assert len(results) == 1
                assert results[0].content == "Success"
                assert results[0].metadata["page_number"] == 2
        finally:
            os.unlink(tmp_path)
