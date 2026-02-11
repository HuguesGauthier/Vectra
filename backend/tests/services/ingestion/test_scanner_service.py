import os
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import TechnicalError
from app.models.enums import ConnectorStatus, DocStatus
from app.schemas.enums import ConnectorType, ScheduleType
from app.services.scanner_service import ScannerService


@pytest.fixture
def mock_db_session():
    # ... existing ...
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ... fixtures ...


@pytest.mark.asyncio
async def test_scan_folder_success_batched(scanner_service, mock_connector_repo, mock_doc_repo, connector_id):
    """Test successful folder scan with batching logic."""

    # 1. Setup Mocks
    mock_connector = MagicMock()
    mock_connector.id = connector_id
    mock_connector.name = "Test Connector"
    mock_connector.description = None
    mock_connector.connector_type = ConnectorType.FILE
    mock_connector.configuration = {}
    mock_connector.is_enabled = True
    mock_connector.schedule_type = ScheduleType.MANUAL
    mock_connector.schedule_cron = None
    mock_connector.chunk_size = 100
    mock_connector.chunk_overlap = 10

    # Response specific
    mock_connector.status = ConnectorStatus.IDLE
    mock_connector.last_error = None
    mock_connector.last_vectorized_at = None
    mock_connector.last_sync_start_at = None
    mock_connector.last_sync_end_at = None

    mock_connector.total_docs_count = 0
    mock_connector.indexed_docs_count = 0
    mock_connector.failed_docs_count = 0
    mock_connector.created_at = datetime.now()
    mock_connector.updated_at = datetime.now()

    # Mock update to return self
    mock_connector_repo.update.return_value = mock_connector
    mock_connector_repo.get_by_id.return_value = mock_connector

    mock_doc_repo.get_by_connector.return_value = []  # Empty DB
    mock_doc_repo.count_by_connector.return_value = 1

    # Mock FS
    found_files = {"test.txt": "/tmp/test.txt"}

    with (
        patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io,
        patch(
            "app.services.scanner_service.ScannerService._determine_file_delta", new_callable=AsyncMock
        ) as mock_delta,
        patch("app.services.scanner_service.ScannerService._safe_emit", new_callable=AsyncMock),
    ):

        mock_io.side_effect = [True, found_files]  # exists, walk
        mock_delta.return_value = ("create", {"file_path": "test.txt", "status": DocStatus.IDLE})

        # 2. Execute
        stats = await scanner_service.scan_folder(connector_id, "/tmp")

        # 3. Verify
        assert stats["added"] == 1
        mock_doc_repo.create_batch.assert_called_once()
        assert scanner_service.db.commit.called


@pytest.mark.asyncio
async def test_scan_folder_zombie_cleanup_batched(scanner_service, mock_doc_repo, mock_connector_repo, connector_id):
    """Test batched deletion and atomic post-commit vector cleanup."""

    mock_connector = MagicMock()
    mock_connector.id = connector_id
    mock_connector_repo.get_by_id.return_value = mock_connector

    # Existing doc in DB
    doc_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.file_path = "gone.txt"
    mock_doc_repo.get_by_connector.return_value = [mock_doc]

    with (
        patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io,
        patch("app.services.scanner_service.ScannerService._safe_emit", new_callable=AsyncMock),
        patch(
            "app.services.scanner_service.ScannerService._safe_delete_vectors", new_callable=AsyncMock
        ) as mock_vector_del,
        patch("app.services.scanner_service.manager.emit_document_deleted", new_callable=AsyncMock),
    ):

        # IO: exists=True, walk=empty
        mock_io.side_effect = [True, {}]

        await scanner_service.scan_folder(connector_id, "/tmp")

        # Verify batch delete was called
        mock_doc_repo.delete_batch.assert_called_once_with([doc_id])
        # Verify vector cleanup happened (should be called because commit succeeded in mock)
        mock_vector_del.assert_called_with(doc_id)


@pytest.mark.asyncio
async def test_determine_file_delta_new(scanner_service, mock_doc_repo, connector_id):
    """Test _determine_file_delta for a new file."""

    rel_path = "hello.md"
    full_path = "/tmp/hello.md"

    with patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io:

        mock_stat = MagicMock()
        mock_stat.st_size = 100
        mock_stat.st_mtime = 123456789
        mock_io.return_value = mock_stat

        action, data = await scanner_service._determine_file_delta(
            rel_path, full_path, None, connector_id, DocStatus.IDLE
        )

        assert action == "create"
        assert data["file_path"] == rel_path
        # assert data["content_hash"] == "hash123" # REMOVED


@pytest.mark.asyncio
async def test_determine_file_delta_unchanged(scanner_service, mock_doc_repo, connector_id):
    """Test _determine_file_delta for an unchanged file."""

    rel_path = "same.md"
    full_path = "/tmp/same.md"

    # Mock Doc has same properties
    mock_doc = MagicMock()
    mock_doc.file_size = 100
    mock_doc.last_modified_at_source = datetime.fromtimestamp(123456789)
    mock_doc.status = DocStatus.IDLE

    with patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io:

        mock_stat = MagicMock()
        mock_stat.st_size = 100
        mock_stat.st_mtime = 123456789  # Same timestamp
        mock_io.return_value = mock_stat

        action, data = await scanner_service._determine_file_delta(
            rel_path, full_path, mock_doc, connector_id, DocStatus.IDLE
        )

        assert action is None
        assert data is None


@pytest.mark.asyncio
async def test_determine_file_delta_changed(scanner_service, mock_doc_repo, connector_id):
    """Test _determine_file_delta for a CHANGED file (size)."""

    rel_path = "changed.md"
    full_path = "/tmp/changed.md"

    # Mock Doc has OLD size
    mock_doc = MagicMock()
    mock_doc.file_size = 50
    mock_doc.last_modified_at_source = datetime.fromtimestamp(123456789)
    mock_doc.status = DocStatus.IDLE

    with patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io:

        mock_stat = MagicMock()
        mock_stat.st_size = 100  # CHANGED SIZE
        mock_stat.st_mtime = 123456789
        mock_io.return_value = mock_stat

        action, data = await scanner_service._determine_file_delta(
            rel_path, full_path, mock_doc, connector_id, DocStatus.IDLE
        )

        assert action == "update"
        assert data["file_size"] == 100
