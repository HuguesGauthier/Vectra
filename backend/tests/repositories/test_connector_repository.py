"""
Tests for ConnectorRepository.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.models.connector import Connector, ConnectorStatus
from app.repositories.connector_repository import ConnectorRepository


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def repository(mock_db):
    return ConnectorRepository(mock_db)


@pytest.mark.asyncio
async def test_get_all_with_stats_empty(repository, mock_db):
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result

    # Act
    result = await repository.get_all_with_stats()

    # Assert
    assert result == []
    assert mock_db.execute.call_count == 1


@pytest.mark.asyncio
async def test_delete_with_relations_success(repository, mock_db):
    # Arrange
    cid = uuid4()
    # 1. exists check
    mock_exists = MagicMock()
    mock_exists.scalar_one.return_value = 1

    # 2. delete docs result
    mock_del_docs = MagicMock()

    # 3. delete links result
    mock_del_links = MagicMock()

    # 4. delete connector result (from base.delete)
    mock_del_conn = MagicMock()
    mock_del_conn.rowcount = 1

    mock_db.execute.side_effect = [mock_exists, mock_del_docs, mock_del_links, mock_del_conn]

    # Act
    success = await repository.delete_with_relations(cid)

    # Assert
    assert success is True
    assert mock_db.execute.call_count == 4


@pytest.mark.asyncio
async def test_delete_with_relations_failure_rollbacks(repository, mock_db):
    # Arrange
    cid = uuid4()
    mock_exists = MagicMock()
    mock_exists.scalar_one.return_value = 1

    mock_db.execute.side_effect = [mock_exists, SQLAlchemyError("Deadlock")]

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.delete_with_relations(cid)

    assert mock_db.rollback.called


@pytest.mark.asyncio
async def test_get_by_statuses_success(repository, mock_db):
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [Connector(name="Test")]
    mock_db.execute.return_value = mock_result

    # Act
    result = await repository.get_by_statuses([ConnectorStatus.IDLE])

    # Assert
    assert len(result) == 1
    assert "status IN" in str(mock_db.execute.call_args[0][0])
