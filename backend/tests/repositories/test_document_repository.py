"""
Tests for DocumentRepository.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.models.enums import DocStatus
from app.repositories.base_repository import MAX_LIMIT
from app.repositories.document_repository import DocumentRepository


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def repository(mock_db):
    return DocumentRepository(mock_db)


@pytest.mark.asyncio
async def test_get_by_connector_respects_max_limit(repository, mock_db):
    # Arrange
    cid = uuid4()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result

    # Act
    # Requesting a huge limit
    await repository.get_by_connector(cid, limit=99999)

    # Assert
    # Check if .limit(1000) was called in the statement
    stmt = mock_db.execute.call_args[0][0]
    assert stmt._limit == MAX_LIMIT


@pytest.mark.asyncio
async def test_search_documents_failure_raises_technical_error(repository, mock_db):
    # Arrange
    mock_db.execute.side_effect = SQLAlchemyError("DB Gone")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.search_documents(search_term="test")


@pytest.mark.asyncio
async def test_update_status_success(repository, mock_db):
    # Arrange
    did = uuid4()
    # Mock update response from base repository would be returned here
    repository.update = AsyncMock(return_value=MagicMock())

    # Act
    result = await repository.update_status(did, DocStatus.INDEXED)

    # Assert
    assert result is not None
    repository.update.assert_called_once_with(did, {"status": DocStatus.INDEXED})


@pytest.mark.asyncio
async def test_count_by_connector_success(repository, mock_db):
    # Arrange
    cid = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_db.execute.return_value = mock_result

    # Act
    count = await repository.count_by_connector(cid)

    # Assert
    assert count == 42
    assert mock_db.execute.called
