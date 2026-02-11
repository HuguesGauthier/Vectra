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
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_connector_repo():
    return AsyncMock()


@pytest.fixture
def mock_doc_repo():
    return AsyncMock()


@pytest.fixture
def mock_vector_service():
    return AsyncMock()


@pytest.fixture
def connector_id():
    return uuid4()


@pytest.fixture
def scanner_service(mock_db_session, mock_connector_repo, mock_doc_repo, mock_vector_service):
    return ScannerService(
        db=mock_db_session,
        connector_repo=mock_connector_repo,
        document_repo=mock_doc_repo,
        vector_service=mock_vector_service,
    )


@pytest.fixture
def mock_connector(connector_id):
    mock = MagicMock()
    mock.id = connector_id
    mock.name = "Test Connector"
    mock.description = None
    mock.connector_type = ConnectorType.LOCAL_FILE
    mock.configuration = {}
    mock.is_enabled = True
    mock.schedule_type = ScheduleType.MANUAL
    mock.schedule_cron = None
    mock.chunk_size = 300
    mock.chunk_overlap = 30
    mock.status = ConnectorStatus.IDLE
    mock.last_error = None
    mock.last_vectorized_at = None
    mock.total_docs_count = 0
    mock.indexed_docs_count = 0
    mock.failed_docs_count = 0
    mock.last_sync_start_at = None
    mock.last_sync_end_at = None
    mock.created_at = datetime.now()
    mock.updated_at = datetime.now()
    return mock


@pytest.mark.asyncio
async def test_scan_folder_success_batched(
    scanner_service, mock_connector_repo, mock_doc_repo, mock_connector, connector_id
):
    """Test successful folder scan with batching logic."""

    # Mock repos
    mock_connector_repo.update.return_value = mock_connector
    mock_connector_repo.get_by_id.return_value = mock_connector

    mock_doc_repo.get_by_connector.return_value = []
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
async def test_scan_folder_zombie_cleanup_batched(
    scanner_service, mock_doc_repo, mock_connector_repo, mock_connector, connector_id
):
    """Test batched deletion and atomic post-commit vector cleanup."""

    mock_connector_repo.get_by_id.return_value = mock_connector
    mock_connector_repo.update.return_value = mock_connector

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
            rel_path, full_path, None, connector_id, DocStatus.IDLE, "local_file"
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
            rel_path, full_path, mock_doc, connector_id, DocStatus.IDLE, "local_file"
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
    mock_doc.id = uuid4()
    mock_doc.file_size = 50
    mock_doc.last_modified_at_source = datetime.fromtimestamp(123456789)
    mock_doc.status = DocStatus.IDLE

    with patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io:

        mock_stat = MagicMock()
        mock_stat.st_size = 100  # CHANGED SIZE
        mock_stat.st_mtime = 123456789
        mock_io.return_value = mock_stat

        action, data = await scanner_service._determine_file_delta(
            rel_path, full_path, mock_doc, connector_id, DocStatus.IDLE, "local_file"
        )

        assert action == "update"
        assert data["file_size"] == 100


@pytest.mark.asyncio
async def test_determine_file_delta_unsupported(scanner_service, connector_id):
    """Test _determine_file_delta for an unsupported file extension."""
    rel_path = "style.css"
    full_path = "/tmp/style.css"

    with patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io:
        mock_stat = MagicMock()
        mock_stat.st_size = 100
        mock_stat.st_mtime = 123456789
        mock_io.return_value = mock_stat

        action, data = await scanner_service._determine_file_delta(
            rel_path, full_path, None, connector_id, DocStatus.IDLE, "local_file"
        )

        assert action == "ignore"
        assert data["status"] == DocStatus.UNSUPPORTED
        assert data["file_metadata"]["reason"] == "Unsupported extension"


@pytest.mark.asyncio
async def test_determine_file_delta_local_folder_csv_blocked(scanner_service, connector_id):
    """Test that CSV files are blocked specifically for local_folder connectors."""
    rel_path = "data.csv"
    full_path = "/tmp/data.csv"

    with patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io:
        mock_stat = MagicMock()
        mock_stat.st_size = 100
        mock_stat.st_mtime = 123456789
        mock_io.return_value = mock_stat

        # Case 1: local_folder connector
        action, data = await scanner_service._determine_file_delta(
            rel_path, full_path, None, connector_id, DocStatus.IDLE, "local_folder"
        )
        assert action == "ignore"
        assert data["status"] == DocStatus.UNSUPPORTED
        assert "not supported in Folder connectors" in data["file_metadata"]["reason"]

        # Case 2: generic file connector (should be supported)
        with patch("app.services.ingestion.utils.IngestionUtils.validate_csv_file", new_callable=AsyncMock) as mock_val:
            mock_val.return_value = []
            action, data = await scanner_service._determine_file_delta(
                rel_path, full_path, None, connector_id, DocStatus.IDLE, "local_file"
            )
            assert action == "create"
            assert data["status"] == DocStatus.IDLE


@pytest.mark.asyncio
async def test_scan_folder_with_unsupported_files(
    scanner_service, mock_connector_repo, mock_doc_repo, mock_connector, connector_id
):
    """Test scan_folder correctly handles and counts unsupported files."""
    mock_connector.connector_type = "local_file"
    mock_connector.schedule_type = "manual"
    mock_connector_repo.get_by_id.return_value = mock_connector
    mock_connector_repo.update.return_value = mock_connector
    mock_doc_repo.get_by_connector.return_value = []
    mock_doc_repo.count_by_connector.return_value = 2

    found_files = {"test.txt": "/tmp/test.txt", "video.mp4": "/tmp/video.mp4"}

    with (
        patch("app.services.scanner_service.ScannerService._run_blocking_io") as mock_io,
        patch("app.services.scanner_service.ScannerService._safe_emit", new_callable=AsyncMock),
    ):
        mock_io.side_effect = [True, found_files]

        # Use the actual _determine_file_delta but mock os.stat and mime detection if needed
        # Or just mock _determine_file_delta for simplicity in this integration-like test
        with patch.object(scanner_service, "_determine_file_delta", new_callable=AsyncMock) as mock_delta:
            mock_delta.side_effect = [
                ("create", {"file_path": "test.txt", "status": DocStatus.IDLE}),
                ("ignore", {"file_path": "video.mp4", "status": DocStatus.UNSUPPORTED}),
            ]

            stats = await scanner_service.scan_folder(connector_id, "/tmp")

            assert stats["added"] == 1
            assert stats["ignored"] == 1
            assert mock_doc_repo.create_batch.call_count == 1
            # Batch create should contain both docs
            created_docs = mock_doc_repo.create_batch.call_args[0][0]
            assert len(created_docs) == 2
