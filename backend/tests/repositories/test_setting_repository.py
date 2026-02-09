"""
Tests for SettingRepository.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.models.setting import Setting
from app.repositories.setting_repository import SettingRepository


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def repository(mock_db):
    return SettingRepository(mock_db)


@pytest.mark.asyncio
async def test_get_by_key_failure(repository, mock_db):
    # Arrange
    mock_db.execute.side_effect = SQLAlchemyError("Connection lost")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.get_by_key("some_key")


@pytest.mark.asyncio
async def test_update_bulk_success(repository, mock_db):
    # Arrange
    updates = {"openai_api_key": "new-key", "theme": "dark"}
    # Mock rowcount for each update call
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.execute.return_value = mock_result

    # Act
    count = await repository.update_bulk(updates)

    # Assert
    assert count == 2
    assert mock_db.commit.called
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_update_bulk_rollback_on_failure(repository, mock_db):
    # Arrange
    updates = {"key1": "val1", "key2": "val2"}
    mock_db.execute.side_effect = SQLAlchemyError("Deadlock")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.update_bulk(updates)

    assert mock_db.rollback.called


@pytest.mark.asyncio
async def test_get_by_group_success(repository, mock_db):
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [Setting(key="k1", group="general")]
    mock_db.execute.return_value = mock_result

    # Act
    results = await repository.get_by_group("general")

    # Assert
    assert len(results) == 1
    # Check that where clause uses group (indirectly via result logic)
    assert len(results) == 1
    assert results[0].group == "general"
