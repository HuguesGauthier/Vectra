import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import EntityNotFound, TechnicalError
from app.services.system_service import SystemService


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def service(tmp_path, mock_db_session):
    # whitelist the temp path fixture
    return SystemService(allowed_base_paths=[str(tmp_path)], db=mock_db_session)


@pytest.mark.asyncio
async def test_open_file_externally_blocked_path(service):
    """Verify that unauthorized paths are blocked."""
    # We use a path that is definitely NOT in tmp_path or project root
    with pytest.raises(TechnicalError) as exc:
        await service.open_file_externally("/etc/passwd")

    assert exc.value.error_code == "UNAUTHORIZED_PATH_ACCESS"


@pytest.mark.asyncio
async def test_open_file_externally_not_found(service, tmp_path):
    """Verify that missing files in safe paths raise EntityNotFound."""
    safe_file = tmp_path / "missing.txt"
    # Even if path is safe, file non-existence raises EntityNotFound
    with pytest.raises(EntityNotFound):
        await service.open_file_externally(str(safe_file))


@pytest.mark.asyncio
async def test_open_file_externally_success(service, tmp_path):
    """Verify that authorized paths call the sync open logic in a thread."""
    safe_file = tmp_path / "report.pdf"

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.resolve", return_value=safe_file),
        patch("app.services.system_service.asyncio.to_thread", new_callable=AsyncMock) as mock_thread,
    ):
        mock_thread.return_value = True

        success = await service.open_file_externally(str(safe_file))

        assert success is True
        mock_thread.assert_called_once()
        assert mock_thread.call_args[0][0] == service._open_sync
        assert mock_thread.call_args[0][1] == safe_file


@pytest.mark.asyncio
async def test_open_file_by_document_id_success(service):
    """Verify document lookup and path reconstruction."""
    doc_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.connector_id = uuid4()
    mock_doc.file_path = "sub/file.txt"

    mock_connector = MagicMock()
    mock_connector.connector_type = "local_folder"
    mock_connector.configuration = {"path": "/tmp/storage"}

    with (
        patch("app.services.system_service.DocumentRepository", return_value=AsyncMock()) as mock_doc_repo_cls,
        patch("app.services.system_service.ConnectorRepository", return_value=AsyncMock()) as mock_conn_repo_cls,
        patch("app.services.system_service.get_full_path_from_connector", return_value="/tmp/storage/sub/file.txt"),
        patch.object(service, "open_file_externally", new_callable=AsyncMock) as mock_open,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.resolve", return_value=Path("/tmp/storage/sub/file.txt")),
    ):
        mock_doc_repo_cls.return_value.get_by_id.return_value = mock_doc
        mock_conn_repo_cls.return_value.get_by_id.return_value = mock_connector
        mock_open.return_value = True

        result = await service.open_file_by_document_id(str(doc_id))

        assert result is True
        expected_path = Path("/tmp/storage/sub/file.txt").resolve()
        expected_base = Path("/tmp/storage").resolve()
        mock_open.assert_called_once()
        args, _ = mock_open.call_args
        assert Path(args[0]).resolve() == expected_path


@pytest.mark.asyncio
async def test_open_file_by_document_id_not_found(service):
    """Verify EntityNotFound when document is missing."""
    doc_id = uuid4()
    with patch("app.services.system_service.DocumentRepository", return_value=AsyncMock()) as mock_repo_cls:
        mock_repo_cls.return_value.get_by_id.return_value = None

        with pytest.raises(EntityNotFound):
            await service.open_file_by_document_id(str(doc_id))
