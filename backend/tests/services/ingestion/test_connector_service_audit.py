import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.connector import Connector
from app.schemas.connector import ConnectorCreate, ConnectorUpdate
from app.schemas.enums import ConnectorStatus, ConnectorType, ScheduleType
import importlib
import app.services.connector_service

importlib.reload(app.services.connector_service)
from app.services.connector_service import MANAGED_UPLOAD_DIR, ConnectorService

# ... imports ...


# Setup simple mocks
@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.db = MagicMock()
    return repo


@pytest.fixture
def mock_scanner():
    return AsyncMock()


@pytest.fixture
def service(mock_repo, mock_scanner):
    return ConnectorService(mock_repo, mock_scanner)


@pytest.mark.asyncio
async def test_security_prevent_arbitrary_file_deletion(service):
    """
    P0 CRITICAL: Verify that the service REFUSES to delete files outside the uploads directory.
    """
    # 1. Setup a connector pointing to a sensitive system file
    connector_id = uuid4()
    sensitive_path = "C:\\Windows\\System32\\drivers\\etc\\hosts.csv" if os.name == "nt" else "/etc/passwd.csv"

    # Use real Connector object
    mock_connector = Connector(
        id=connector_id,
        connector_type=ConnectorType.LOCAL_FILE,
        configuration={"path": sensitive_path},
        status=ConnectorStatus.IDLE,
        name="Sensitive",
    )

    service.connector_repo.get_by_id.return_value = mock_connector
    service.connector_repo.update.return_value = mock_connector

    # 2. Update to a new path (triggering 'cleanup' of old path)
    new_path = os.path.abspath(os.path.join(MANAGED_UPLOAD_DIR, "new_file.csv"))
    update_payload = ConnectorUpdate(configuration={"path": new_path})

    # Mock OS functions to simulate file existence
    with (
        patch("app.services.connector_service.ConnectorService._validate_folder_path", new_callable=AsyncMock),
        patch("app.services.connector_service.os.path.exists", return_value=True),
        patch("app.services.connector_service.os.path.isfile", return_value=True),
        patch("app.services.connector_service.os.path.isdir", return_value=True),
        patch("app.services.connector_service.os.remove") as mock_remove,
    ):

        # 3. Perform Update
        await service.update_connector(connector_id, update_payload)

        # 4. ASSERT: Remove should NOT have been called for sensitive path
        mock_remove.assert_not_called()


@pytest.mark.asyncio
async def test_security_allow_managed_file_deletion(service):
    """
    P0: Verify that deletion IS allowed for files in managed directory.
    """
    connector_id = uuid4()
    # Create a path that IS inside the managed dir
    safe_path = os.path.abspath(os.path.join(MANAGED_UPLOAD_DIR, "safefile.csv"))

    # Use real Connector object
    mock_connector = Connector(
        id=connector_id,
        connector_type=ConnectorType.LOCAL_FILE,
        configuration={"path": safe_path},
        status=ConnectorStatus.IDLE,
        name="Safe",
    )

    service.connector_repo.get_by_id.return_value = mock_connector
    service.connector_repo.update.return_value = mock_connector

    # Update to trigger cleanup
    new_path = os.path.abspath(os.path.join(MANAGED_UPLOAD_DIR, "other.csv"))
    update_payload = ConnectorUpdate(configuration={"path": new_path})

    with (
        patch("app.services.connector_service.ConnectorService._validate_folder_path", new_callable=AsyncMock),
        patch("app.services.connector_service.os.path.exists", return_value=True),
        patch("app.services.connector_service.os.path.isfile", return_value=True),
        patch("app.services.connector_service.os.path.isdir", return_value=True),
        patch("app.services.connector_service.os.remove") as mock_remove,
    ):

        await service.update_connector(connector_id, update_payload)

        # Yield to allow background task (create_task) to run
        await asyncio.sleep(0.1)

        # Assert REMOVE WAS CALLED
        mock_remove.assert_called_once_with(safe_path)


@pytest.mark.asyncio
async def test_cron_priority(service):
    """
    Verify explicit schedule_cron takes precedence over schedule_type defaults.
    """
    payload = ConnectorCreate(
        name="Test",
        connector_type=ConnectorType.LOCAL_FILE,
        schedule_type=ScheduleType.CRON,
        # Explicit cron custom different from daily (0 0 * * *)
        schedule_cron="15 14 * * *",
        configuration={"path": "foo"},
    )

    mock_connector_data = payload.model_dump()
    mock_connector_data.update(
        {
            "id": uuid4(),
            "created_at": None,
            "updated_at": None,
            "last_vectorized_at": None,
            "total_docs_count": 0,
            "indexed_docs_count": 0,
            "failed_docs_count": 0,
            "status": ConnectorStatus.IDLE,
        }
    )

    mock_obj = MagicMock()
    # Use real Connector object (SQLModel) specifically locally created for test
    # This avoids MagicMock issues with Pydantic validation
    mock_connector = Connector(**mock_connector_data)
    service.connector_repo.create.return_value = mock_connector

    with (
        patch.object(service, "_validate_file_path", new_callable=AsyncMock),
        patch.object(service, "_validate_folder_path", new_callable=AsyncMock),
        patch("app.services.connector_service.manager", new_callable=AsyncMock),
    ):
        await service.create_connector(payload)

    # Check that repo.create was called with our CUSTOM cron data
    call_args = service.connector_repo.create.call_args[0][0]
    assert call_args["schedule_cron"] == "15 14 * * *"


@pytest.mark.asyncio
async def test_manual_schedule_clears_cron(service):
    """
    Regression test: Selecting 'manual' should explicitly set schedule_cron to None.
    """
    connector_id = uuid4()

    # Existing connector has a schedule
    mock_connector = Connector(
        id=connector_id,
        connector_type=ConnectorType.LOCAL_FILE,
        schedule_type=ScheduleType.CRON,
        schedule_cron="0 0 * * *",
        configuration={"path": "foo"},
        status=ConnectorStatus.IDLE,
        name="Regression Test",
        created_at=None,
        updated_at=None,
        total_docs_count=0,
        indexed_docs_count=0,
        failed_docs_count=0,
    )

    service.connector_repo.get_by_id.return_value = mock_connector
    service.connector_repo.update.return_value = mock_connector

    # Update to Manual
    payload = ConnectorUpdate(schedule_type=ScheduleType.MANUAL)

    with patch("app.services.connector_service.manager", new_callable=AsyncMock):
        await service.update_connector(connector_id, payload)

    # Verify we tried to save schedule_cron=None
    call_args = service.connector_repo.update.call_args[0][1]
    assert "schedule_cron" in call_args
    assert call_args["schedule_cron"] is None
