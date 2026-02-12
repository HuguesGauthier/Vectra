"""
Unit tests for ConnectorSyncLogRepository.
"""

from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.repositories.connector_sync_log_repository import ConnectorSyncLogRepository
from app.models.connector_sync_log import ConnectorSyncLog


@pytest.fixture
def sync_log_repo(mock_db_session):
    return ConnectorSyncLogRepository(mock_db_session)


@pytest.mark.asyncio
async def test_create_sync_log(sync_log_repo, mock_db_session):
    """Test creating a sync log."""
    connector_id = uuid4()

    # Mock add/commit/refresh
    mock_db_session.add = MagicMock()
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    log = await sync_log_repo.create_log(connector_id)

    assert log.connector_id == connector_id
    assert log.status == "syncing"
    assert log.documents_synced == 0
    assert log.sync_time is not None


@pytest.mark.asyncio
async def test_update_sync_log(sync_log_repo, mock_db_session):
    """Test updating a sync log."""
    log_id = uuid4()
    # Mock objects need to be async compatible if the repo awaits them
    log = ConnectorSyncLog(id=log_id, status="syncing", documents_synced=0, sync_time=datetime.now())

    # Mock get
    mock_db_session.get = AsyncMock(return_value=log)

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()

    updated_log = await sync_log_repo.update_log(log_id, status="success", documents_synced=10)

    assert updated_log.status == "success"
    assert updated_log.documents_synced == 10
