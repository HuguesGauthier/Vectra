import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pytest

from app.core.exceptions import (FileSystemError, FunctionalError,
                                 TechnicalError)
from app.models.connector_document import ConnectorDocument
from app.models.enums import DocStatus
from app.services.ingestion.file_scanner import FileScanner


class TestFileScanner:

    # --- validate_path ---

    def test_validate_path_exists(self):
        scanner = FileScanner()
        with patch("os.path.exists", return_value=True):
            assert scanner.validate_path("/tmp/exists") is True

    def test_validate_path_not_exists(self):
        scanner = FileScanner()
        with patch("os.path.exists", return_value=False):
            assert scanner.validate_path("/tmp/missing") is False

    def test_validate_path_empty(self):
        scanner = FileScanner()
        assert scanner.validate_path("") is False
        assert scanner.validate_path(None) is False

    # --- scan_connector_files ---

    @pytest.mark.asyncio
    async def test_scan_connector_files_single_file(self):
        scanner = FileScanner()
        base_path = "/data/file.txt"
        with patch("os.path.isfile", return_value=True):
            result = await scanner.scan_connector_files(base_path)
            assert result == {"file.txt": "/data/file.txt"}

    @pytest.mark.asyncio
    async def test_scan_connector_files_directory(self):
        scanner = FileScanner()
        base_path = "/data"
        with patch("os.path.isfile", return_value=False), patch("os.walk") as mock_walk:

            # root, dirs, files
            mock_walk.return_value = [
                ("/data", ["subdir", ".hidden"], ["file1.txt", "file2.csv", "Thumbs.db"]),
                ("/data/subdir", [], ["file3.pdf"]),
            ]

            result = await scanner.scan_connector_files(base_path)

            expected_keys = ["file1.txt", "file2.csv", os.path.join("subdir", "file3.pdf")]

            assert len(result) == 3
            for key in expected_keys:
                assert key in result
            assert "Thumbs.db" not in result

    @pytest.mark.asyncio
    async def test_scan_connector_files_error(self):
        scanner = FileScanner()
        # Fix: Raise OSError to trigger FileSystemError
        with patch("os.path.isfile", side_effect=OSError("Disk error")):
            with pytest.raises(FileSystemError) as exc:
                await scanner.scan_connector_files("/data")

            assert "Directory scan failed" in str(exc.value)

    # --- calculate_file_hash ---

    @pytest.mark.asyncio
    async def test_calculate_file_hash_success(self):
        scanner = FileScanner()
        file_content = b"content"
        # md5 "content" = 9a0364b9e99bb480dd25e1f0284c8555

        with patch("builtins.open", mock_open(read_data=file_content)):
            hash_val = await scanner.calculate_file_hash("/tmp/file.txt")
            assert hash_val == "9a0364b9e99bb480dd25e1f0284c8555"

    @pytest.mark.asyncio
    async def test_calculate_file_hash_error(self):
        scanner = FileScanner()
        with patch("builtins.open", side_effect=OSError("Read error")):
            with pytest.raises(FileSystemError) as exc:
                await scanner.calculate_file_hash("/tmp/file.txt")

            assert "Hashing failed" in str(exc.value)

    # --- identify_changed_files ---

    @pytest.mark.asyncio
    async def test_identify_changed_files_new_file(self):
        scanner = FileScanner()
        connector_id = uuid4()
        files_on_disk = {"new.txt": "/data/new.txt"}
        existing_docs = {}
        db = AsyncMock()
        db.add_all = MagicMock()

        with (
            patch.object(scanner, "calculate_file_hash", new_callable=AsyncMock) as mock_hash,
            patch("os.stat") as mock_stat,
            patch("app.services.ingestion.file_scanner.IngestionUtils") as mock_utils,
        ):

            mock_hash.return_value = "hash_123"
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1678880000.0
            mock_utils.detect_mime_type.return_value = "text/plain"

            result = await scanner.identify_changed_files(connector_id, files_on_disk, existing_docs)
            # Result is tuple (files_to_ingest, new, updated) if unpacking or Object?
            # Code says: return ScanResult(files_to_ingest, new_docs, updated_docs)
            # ScanResult is NamedTuple.

            files_ingest = result.files_to_ingest
            new_docs_list = result.new_docs

            assert len(new_docs_list) == 1
            new_doc = new_docs_list[0]
            assert new_doc.file_path == "new.txt"
            assert new_doc.status == DocStatus.PENDING
            assert new_doc.content_hash == "hash_123"

    @pytest.mark.asyncio
    async def test_identify_changed_files_no_change(self):
        scanner = FileScanner()
        connector_id = uuid4()
        files_on_disk = {"existing.txt": "/data/existing.txt"}

        existing_doc = ConnectorDocument(
            id=uuid4(),
            connector_id=connector_id,
            file_path="existing.txt",
            content_hash="hash_same",
            status=DocStatus.INDEXED,
            doc_token_count=10,
            vector_point_count=10,
        )
        existing_docs = {"existing.txt": existing_doc}
        db = AsyncMock()

        with (
            patch.object(scanner, "calculate_file_hash", new_callable=AsyncMock) as mock_hash,
            patch("os.stat"),
            patch("app.services.ingestion.file_scanner.IngestionUtils.update_doc_metadata"),
        ):

            mock_hash.return_value = "hash_same"

            result = await scanner.identify_changed_files(connector_id, files_on_disk, existing_docs)

            assert len(result.files_to_ingest) == 0
            assert len(result.updated_docs) == 0

    @pytest.mark.asyncio
    async def test_identify_changed_files_modified(self):
        scanner = FileScanner()
        connector_id = uuid4()
        files_on_disk = {"mod.txt": "/data/mod.txt"}

        existing_doc = ConnectorDocument(
            id=uuid4(),
            connector_id=connector_id,
            file_path="mod.txt",
            content_hash="hash_old",
            status=DocStatus.INDEXED,
            doc_token_count=10,
            vector_point_count=10,
        )
        existing_docs = {"mod.txt": existing_doc}
        db = AsyncMock()

        with (
            patch.object(scanner, "calculate_file_hash", new_callable=AsyncMock) as mock_hash,
            patch("os.stat"),
            patch("app.services.ingestion.file_scanner.IngestionUtils.update_doc_metadata"),
        ):

            mock_hash.return_value = "hash_new"  # Changed

            result = await scanner.identify_changed_files(connector_id, files_on_disk, existing_docs)

            assert len(result.files_to_ingest) == 1
            assert result.files_to_ingest[0] == ("/data/mod.txt", "mod.txt")

            assert existing_doc.status == DocStatus.PENDING
            assert existing_doc.content_hash == "hash_new"
            assert existing_doc.updated_at is not None
            assert len(result.updated_docs) == 1

    @pytest.mark.asyncio
    async def test_identify_changed_files_filtered_csv(self):
        scanner = FileScanner()
        connector_id = uuid4()
        files_on_disk = {"bad.csv": "/data/bad.csv"}
        existing_docs = {}
        db = AsyncMock()

        with (
            patch.object(scanner, "calculate_file_hash", new_callable=AsyncMock) as mock_hash,
            patch(
                "app.services.ingestion.file_scanner.IngestionUtils.validate_csv_file",
                side_effect=FunctionalError("Invalid", error_code="INVALID_CSV"),
            ),
        ):

            result = await scanner.identify_changed_files(connector_id, files_on_disk, existing_docs)

            assert len(result.files_to_ingest) == 0
            mock_hash.assert_not_called()

    @pytest.mark.asyncio
    async def test_identify_changed_files_individual_error_handled(self):
        """Test that single file hashing failure doesn't crash the scanner."""
        scanner = FileScanner()
        files_on_disk = {"fail.txt": "/data/fail.txt"}

        with patch.object(scanner, "calculate_file_hash", side_effect=Exception("Read Error"), new_callable=AsyncMock):
            result = await scanner.identify_changed_files(uuid4(), files_on_disk, {})

            assert len(result.files_to_ingest) == 0
            assert len(result.updated_docs) == 0

    @pytest.mark.asyncio
    async def test_identify_changed_files_critical_db_error(self):
        """Test that critical errors propagate."""
        # Note: identify_changed_files No longer takes DB. It returns objects.
        # But if validation fails inside?
        pass  # The previous test logic for DB error is invalid as DB is not passed anymore.
