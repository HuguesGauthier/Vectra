import os
import sys
from unittest.mock import MagicMock, mock_open, patch
from uuid import uuid4

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

import pandas as pd
import pytest

from app.core.exceptions import FileSystemError, FunctionalError, TechnicalError
from app.models.connector_document import ConnectorDocument
from app.services.ingestion.utils import IngestionUtils


class TestIngestionUtils:

    # --- estimate_tokens ---
    def test_estimate_tokens(self):
        assert IngestionUtils.estimate_tokens("word") == 1
        assert IngestionUtils.estimate_tokens("") == 0
        assert IngestionUtils.estimate_tokens("12345678") == 2

    # --- detect_mime_type ---
    def test_detect_mime_type(self):
        assert IngestionUtils.detect_mime_type("file.csv") == "text/csv"
        # Test fallback
        assert IngestionUtils.detect_mime_type("unknown.xyz") == "application/octet-stream"
        # Test registered
        with patch("mimetypes.guess_type", return_value=("image/png", None)):
            assert IngestionUtils.detect_mime_type("test.png") == "image/png"

    # --- update_doc_metadata ---
    def test_update_doc_metadata_success(self):
        doc = ConnectorDocument(id=uuid4(), connector_id=uuid4(), file_path="test.txt")
        full_path = "/tmp/test.txt"

        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1600000000

            IngestionUtils.update_doc_metadata(doc, full_path)

            assert doc.file_size == 100
            assert doc.mime_type == "text/plain"  # inferred from extension in path
            assert doc.file_metadata["original_name"] == "test.txt"

    def test_update_doc_metadata_fail(self):
        doc = ConnectorDocument(id=uuid4(), connector_id=uuid4(), file_path="test.txt")
        with patch("os.stat", side_effect=OSError("Disk error")):
            # Should log warning but not raise
            IngestionUtils.update_doc_metadata(doc, "fail.txt")
            assert doc.file_size is None

    @pytest.mark.asyncio
    async def test_update_doc_metadata_async(self):
        doc = ConnectorDocument(id=uuid4(), connector_id=uuid4(), file_path="test.txt")
        full_path = "/tmp/test.txt"

        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1600000000

            await IngestionUtils.update_doc_metadata_async(doc, full_path)

            assert doc.file_size == 100

    # --- validate_csv_file ---

    # --- validate_csv_file ---

    @pytest.mark.asyncio
    async def test_validate_csv_success(self):
        """Test validation with valid CSV via mocking pandas."""
        # Simple sample DataFrame
        df_sample = pd.DataFrame({"id": [1, 2], "val": ["a", "b"]})

        # We need to mock:
        # 1. os.path.exists
        # 2. pd.read_csv (called twice: once for nrows=10, once for chunks)

        with patch("os.path.exists", return_value=True), patch("pandas.read_csv") as mock_read:

            # Setup mock behavior
            # First call (nrows=10) -> returns df_sample
            # Second call (chunksize) -> returns iterator of chunks

            # Iterator mock
            chunk_mock = MagicMock()
            chunk_mock.__iter__.return_value = [df_sample]

            # Side effect for sequential calls
            mock_read.side_effect = [df_sample, [df_sample]]

            schema = await IngestionUtils.validate_csv_file("test.csv")

            assert len(schema) == 2
            assert schema[0]["name"] == "id"

    @pytest.mark.asyncio
    async def test_validate_csv_missing_id(self):
        df_bad = pd.DataFrame({"col": [1]})
        with patch("os.path.exists", return_value=True), patch("pandas.read_csv", return_value=df_bad):

            with pytest.raises(FunctionalError) as exc:
                await IngestionUtils.validate_csv_file("test.csv")
            assert "missing required 'id'" in str(exc.value)

    @pytest.mark.asyncio
    async def test_validate_csv_duplicates(self):
        df_dupe = pd.DataFrame({"id": [1, 1]})
        with patch("os.path.exists", return_value=True), patch("pandas.read_csv") as mock_read:

            # Header peek
            mock_read.side_effect = [df_dupe, [df_dupe]]  # Used twice (peek + chunk)

            with pytest.raises(FunctionalError) as exc:
                await IngestionUtils.validate_csv_file("dupe.csv")
            assert "Duplicate IDs" in str(exc.value)

    @pytest.mark.asyncio
    async def test_validate_csv_duplicates_inter_chunk(self):
        """Test duplicates across chunks."""
        df_1 = pd.DataFrame({"id": [1, 2]})
        df_2 = pd.DataFrame({"id": [3, 1]})  # 1 is duplicate from chunk 1

        with patch("os.path.exists", return_value=True), patch("pandas.read_csv") as mock_read:

            # Peek called first
            mock_read.side_effect = [df_1, [df_1, df_2]]

            with pytest.raises(FunctionalError) as exc:
                await IngestionUtils.validate_csv_file("chunked_dupe.csv")
            assert "Duplicate IDs" in str(exc.value)

    @pytest.mark.asyncio
    async def test_validate_csv_not_found(self):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileSystemError):
                await IngestionUtils.validate_csv_file("missing.csv")
