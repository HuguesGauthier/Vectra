"""
Tests for ChatRepository.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.repositories.chat_repository import (LLAMA_INDEX_CHAT_TABLE,
                                              ChatRepository)


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def repository(mock_db):
    return ChatRepository(mock_db)


@pytest.mark.asyncio
async def test_get_session_message_count_success(repository, mock_db):
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_db.execute.return_value = mock_result

    # Act
    count = await repository.get_session_message_count("test-session")

    # Assert
    assert count == 5
    mock_db.execute.assert_called_once()
    assert "SELECT COUNT(*)" in mock_db.execute.call_args[0][0].text


@pytest.mark.asyncio
async def test_clear_history_success(repository, mock_db):
    # Arrange
    # First call to count
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 5

    # Second call to delete
    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 5

    mock_db.execute.side_effect = [mock_count_result, mock_delete_result]

    # Act
    success = await repository.clear_history("test-session")

    # Assert
    assert success is True
    assert mock_db.commit.called
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_clear_history_no_records(repository, mock_db):
    # Arrange
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0
    mock_db.execute.return_value = mock_count_result

    # Act
    success = await repository.clear_history("test-session")

    # Assert
    assert success is False
    assert mock_db.execute.call_count == 1
    assert not mock_db.commit.called


@pytest.mark.asyncio
async def test_clear_history_failure_rollbacks(repository, mock_db):
    # Arrange
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 5
    mock_db.execute.side_effect = [mock_count_result, SQLAlchemyError("DB Error")]

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.clear_history("test-session")

    assert mock_db.rollback.called
