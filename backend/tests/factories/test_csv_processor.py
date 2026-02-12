"""
Tests for CSV processor with edge cases.
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.factories.processors.csv_processor import CsvProcessor


class TestCsvProcessorSuccess:
    """Success path tests."""

    @pytest.mark.asyncio
    async def test_process_valid_csv_success(self):
        """Valid CSV should process successfully."""
        # Create temporary CSV
        csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            processor = CsvProcessor()
            results = await processor.process(tmp_path)

            assert len(results) == 1
            doc = results[0]
            assert doc.success is True
            assert doc.metadata["row_count"] == 2
            assert doc.metadata["column_count"] == 3
            assert "column_hash" in doc.metadata
            assert "columns" not in doc.metadata  # P0 security: no leaks
            assert doc.metadata["truncated"] is False
            assert doc.metadata["encoding_used"] == "utf-8"
            assert "Alice" in doc.content
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_process_tsv_file(self):
        """TSV files should be supported."""
        tsv_content = "name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA\n"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tsv") as tmp:
            tmp.write(tsv_content)
            tmp_path = tmp.name

        try:
            processor = CsvProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is True
            assert doc.metadata["row_count"] == 2
            assert doc.metadata["column_count"] == 3
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_process_at_limit_marked_as_potentially_truncated(self):
        """CSV with exactly MAX_ROWS might be truncated (could have more rows)."""
        rows = 100_000  # Exactly at limit
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            tmp.write("col1,col2\n")
            for i in range(rows):
                tmp.write(f"{i},value{i}\n")
            tmp_path = tmp.name

        try:
            processor = CsvProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is True
            assert doc.metadata["row_count"] == 100_000
            # When we hit exactly MAX_ROWS, we assume truncation (file might have more)
            assert doc.metadata["truncated"] is True
        finally:
            os.unlink(tmp_path)


class TestCsvProcessorTruncation:
    """Truncation behavior tests."""

    @pytest.mark.asyncio
    async def test_process_oversized_csv_truncates(self):
        """CSV exceeding row limit should be truncated during read."""
        # Create CSV with more than 100k rows
        rows = 100_005  # Just over limit
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            tmp.write("col1,col2\n")
            for i in range(rows):
                tmp.write(f"{i},value{i}\n")
            tmp_path = tmp.name

        try:
            processor = CsvProcessor()
            results = await processor.process(tmp_path)

            doc = results[0]
            assert doc.success is True
            # pandas nrows=100_000 means only 100k rows are read
            assert doc.metadata["row_count"] == 100_000
            # Since we hit the limit, we assume truncation occurred
            assert doc.metadata["truncated"] is True
        finally:
            os.unlink(tmp_path)


class TestCsvProcessorFailures:
    """Failure path tests."""

    @pytest.mark.asyncio
    async def test_process_nonexistent_file_raises(self):
        """Non-existent file should raise FileNotFoundError."""
        processor = CsvProcessor()

        results = await processor.process("/nonexistent/file.csv")
        assert results[0].success is False
        assert "not found" in results[0].error_message.lower()

    @pytest.mark.asyncio
    async def test_process_file_too_large_fails(self):
        """File exceeding size limit should raise ValueError."""
        # Create 60MB CSV (exceeds 50MB limit)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            tmp.write("data\n")
            # Write 60MB of data
            tmp.write("x" * (60 * 1024 * 1024))
            tmp_path = tmp.name

        try:
            processor = CsvProcessor()
            results = await processor.process(tmp_path)
            assert results[0].success is False
            assert "too large" in results[0].error_message.lower()
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_get_supported_extensions(self):
        """Should support csv and tsv extensions."""
        processor = CsvProcessor()
        extensions = processor.get_supported_extensions()
        assert "csv" in extensions
        assert "tsv" in extensions
