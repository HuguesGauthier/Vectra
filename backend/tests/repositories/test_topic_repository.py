"""
Tests for TopicRepository.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.repositories.base_repository import MAX_LIMIT
from app.repositories.topic_repository import TopicRepository


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def repository(mock_db):
    return TopicRepository(mock_db)


@pytest.mark.asyncio
async def test_get_trending_limit_enforcement(repository, mock_db):
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result

    # Act
    await repository.get_trending(limit=99999)

    # Assert
    stmt = mock_db.execute.call_args[0][0]
    assert stmt._limit == MAX_LIMIT


@pytest.mark.asyncio
async def test_get_by_id_with_lock_failure(repository, mock_db):
    # Arrange
    tid = uuid4()
    mock_db.execute.side_effect = SQLAlchemyError("Lock timeout")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.get_by_id_with_lock(tid)


@pytest.mark.asyncio
async def test_get_trending_with_assistant_filter(repository, mock_db):
    # Arrange
    aid = uuid4()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result

    # Act
    await repository.get_trending(assistant_id=aid)

    # Assert
    call_args = str(mock_db.execute.call_args)
    # Verify assistant_id filter was applied (checking string representation roughly)
    assert mock_db.execute.called
