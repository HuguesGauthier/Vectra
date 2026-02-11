import asyncio
import os
import sys
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (DuplicateError, EntityNotFound,
                                 FunctionalError, InternalDataCorruption)
from app.models.connector import Connector
from app.models.enums import ConnectorStatus
from app.repositories.connector_repository import ConnectorRepository
from app.schemas.connector import ConnectorCreate, ConnectorUpdate
from app.services.connector_service import ConnectorService
from app.services.settings_service import SettingsService
from app.services.vector_service import VectorService

# --- Fixtures ---


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_connector_repo(mock_db_session):
    repo = MagicMock(spec=ConnectorRepository)
    repo.db = mock_db_session
    return repo


@pytest.fixture
def mock_scanner_service():
    service = MagicMock()
    return service


@pytest.fixture
def mock_settings_service(mock_db_session):
    ss = MagicMock()
    ss.get_value = AsyncMock()
    return ss


@pytest.fixture
def mock_vector_service(mock_settings_service):
    vs = MagicMock()
    vs.get_collection_name = AsyncMock(return_value="test_collection")
    vs.get_async_qdrant_client = MagicMock()
    return vs


@pytest.fixture
def connector_service(mock_connector_repo, mock_scanner_service, mock_vector_service, mock_settings_service):
    return ConnectorService(
        connector_repo=mock_connector_repo,
        scanner_service=mock_scanner_service,
        vector_service=mock_vector_service,
        settings_service=mock_settings_service,
    )


@pytest.fixture
def mock_ws_manager():
    with patch("app.services.connector_service.manager") as manager_mock:
        manager_mock.emit_connector_created = AsyncMock()
        manager_mock.emit_connector_updated = AsyncMock()
        manager_mock.emit_connector_deleted = AsyncMock()
        yield manager_mock


def mock_blocking_io(func, *args):
    if func == os.path.exists:
        return True
    if func == os.path.isdir:
        return True
    if func == os.remove:
        return None
    return None


# --- Tests ---


@pytest.mark.asyncio
async def test_create_connector_nominal(connector_service, mock_connector_repo, mock_ws_manager):
    """Test nominal creation with background scan schedule."""
    data = ConnectorCreate(
        name="Folder", connector_type="local_file", configuration={"path": "/tmp", "recursive": True}
    )

    # Mock Repo
    new_cnt = Connector(id=uuid4(), name="Folder", connector_type="local_file")
    mock_connector_repo.create = AsyncMock(return_value=new_cnt)

    with (
        patch("asyncio.to_thread", side_effect=mock_blocking_io),
        patch.object(connector_service, "_safe_background_scan", new_callable=AsyncMock) as mock_scan,
    ):

        result = await connector_service.create_connector(data)

        # Verify Repo calls
        mock_connector_repo.create.assert_called_once()

        # Verify background scan triggered
        mock_scan.assert_called_once()
        assert result.name == "Folder"


@pytest.mark.asyncio
async def test_get_connectors(connector_service, mock_connector_repo):
    """Test retrieval."""
    c1 = Connector(id=uuid4(), name="C1", connector_type="local_file")
    # We use the repo method we actually call
    mock_connector_repo.get_all_with_stats = AsyncMock(return_value=[c1])

    connectors = await connector_service.get_connectors()

    assert len(connectors) == 1
    assert connectors[0].name == "C1"


@pytest.mark.asyncio
async def test_update_connector_nominal(connector_service, mock_connector_repo, mock_ws_manager):
    """Test update with side effects."""
    cid = uuid4()
    c = Connector(
        id=cid,
        name="Test Conn",
        connector_type="local_file",
        configuration={"path": "/old", "connector_acl": ["User"]},
        status=ConnectorStatus.IDLE,
    )

    mock_connector_repo.get_by_id = AsyncMock(return_value=c)
    mock_connector_repo.update = AsyncMock(return_value=c)

    update = ConnectorUpdate(configuration={"path": "/new", "connector_acl": ["Admin"]})

    with (
        patch("asyncio.to_thread", side_effect=mock_blocking_io),
        patch.object(connector_service, "_safe_delete_file", new_callable=AsyncMock) as mock_delete,
        patch.object(connector_service, "_safe_update_acl", new_callable=AsyncMock) as mock_acl,
        patch.object(connector_service, "_safe_background_scan", new_callable=AsyncMock) as mock_scan,
    ):

        await connector_service.update_connector(cid, update)

        # Verification
        mock_connector_repo.update.assert_called_once()
        # Background tasks should have been called
        mock_delete.assert_called_once()
        mock_acl.assert_called_once()


@pytest.mark.asyncio
async def test_delete_connector_cleanup(connector_service, mock_connector_repo, mock_ws_manager):
    """Test deletion spawns cleanup tasks."""
    cid = uuid4()
    c = Connector(
        id=cid, name="Test Conn", connector_type="local_file", configuration={"path": "/data", "ai_provider": "gemini"}
    )

    mock_connector_repo.get_by_id = AsyncMock(return_value=c)
    mock_connector_repo.delete_with_relations = AsyncMock()

    with (
        patch.object(connector_service, "_safe_delete_file", new_callable=AsyncMock) as mock_delete,
        patch.object(connector_service, "_safe_delete_vectors", new_callable=AsyncMock) as mock_vectors,
    ):
        await connector_service.delete_connector(cid)

        # Cleanup file + Cleanup vectors
        mock_vectors.assert_called_once()
        mock_connector_repo.delete_with_relations.assert_called_once_with(cid)


@pytest.mark.asyncio
async def test_delete_connector_security_guard(connector_service, mock_connector_repo):
    """Worst Case: Deletion attempt on non-managed path should skip file deletion."""
    connector_id = uuid4()
    # Path OUTSIDE MANAGED_UPLOAD_DIR
    fake_connector = Connector(
        id=connector_id,
        connector_type="local_file",
        configuration={"path": "/etc/passwd"}
    )
    mock_connector_repo.get_by_id = AsyncMock(return_value=fake_connector)
    mock_connector_repo.delete_with_relations = AsyncMock()

    with patch.object(connector_service, "_safe_delete_file", new_callable=AsyncMock) as mock_delete:
        # Act
        await connector_service.delete_connector(connector_id)

        # Assert
        mock_delete.assert_not_called()
        mock_connector_repo.delete_with_relations.assert_called_once()


@pytest.mark.asyncio
async def test_update_critical_config_stops_connector(connector_service, mock_connector_repo, mock_ws_manager):
    """Stablity: Updating folder path should auto-stop the connector if it's running."""
    connector_id = uuid4()
    old_config = {"path": "temp_uploads/old"}
    new_config = {"path": "temp_uploads/new"}

    db_connector = Connector(
        id=connector_id,
        name="Update Test",
        connector_type="local_folder",
        configuration=old_config,
        status=ConnectorStatus.SYNCING # Running
    )

    mock_connector_repo.get_by_id = AsyncMock(return_value=db_connector)
    mock_connector_repo.update = AsyncMock(return_value=db_connector)

    update_data = ConnectorUpdate(configuration=new_config)

    with patch("asyncio.to_thread", return_value=True):
        # Act
        await connector_service.update_connector(connector_id, update_data)

        # Assert
        # Verify that 'status': 'idle' was passed to repo.update
        args, kwargs = mock_connector_repo.update.call_args
        assert args[1]["status"] == ConnectorStatus.IDLE


@pytest.mark.asyncio
async def test_manual_scan_connector(connector_service, mock_connector_repo, mock_scanner_service):
    """Test manual scan trigger."""
    cid = uuid4()
    c = Connector(id=cid, name="Test Conn", connector_type="local_file", configuration={"path": "/data"})

    mock_connector_repo.get_by_id = AsyncMock(return_value=c)
    mock_scanner_service.scan_folder = AsyncMock()

    await connector_service.scan_connector(cid)
    mock_scanner_service.scan_folder.assert_awaited()


@pytest.mark.asyncio
async def test_safe_wrappers(connector_service):
    """Directly test private safe wrappers."""
    # File Delete
    with patch("asyncio.to_thread", side_effect=mock_blocking_io) as mock_io:
        await connector_service._safe_delete_file("/path")
        assert mock_io.call_count == 2

    # ACL Update
    with patch(
        "app.services.ingestion_service.IngestionService.update_connector_acl", new_callable=AsyncMock
    ) as mock_acl:
        await connector_service._safe_update_acl(uuid4(), [], {"ai_provider": "gemini"})
        mock_acl.assert_awaited()
