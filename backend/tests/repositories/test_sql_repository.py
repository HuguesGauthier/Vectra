"""
Tests for SQLRepository (Generic).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, SQLModel

from app.core.exceptions import TechnicalError
from app.repositories.base_repository import MAX_LIMIT
from app.repositories.sql_repository import SQLRepository


# Mock Model for testing
class MockModel(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str


class MockCreate(SQLModel):
    name: str


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def repository(mock_db):
    return SQLRepository(MockModel, mock_db)


@pytest.mark.asyncio
async def test_create_with_pydantic_model(repository, mock_db):
    # Arrange
    create_data = MockCreate(name="Test Item")

    # Act
    result = await repository.create(create_data)

    # Assert
    assert mock_db.add.called
    assert mock_db.commit.called
    # We can't easily check the entity attributes because it's created inside,
    # but we can verify the mock add was called.


@pytest.mark.asyncio
async def test_get_all_enforces_limit(repository, mock_db):
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result

    # Act
    await repository.get_all(limit=99999)

    # Assert
    stmt = mock_db.execute.call_args[0][0]
    assert stmt._limit == MAX_LIMIT


@pytest.mark.asyncio
async def test_db_error_raises_technical_error(repository, mock_db):
    # Arrange
    mock_db.execute.side_effect = SQLAlchemyError("Boom")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_update_rollback_on_failure(repository, mock_db):
    # Arrange
    entity_id = uuid4()
    # Mock get_by_id logic to return an entity first
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MockModel(id=1, name="Old")
    mock_db.execute.return_value = mock_result

    # Fail on commit
    mock_db.commit.side_effect = SQLAlchemyError("Lock error")

    # Act & Assert
    with pytest.raises(TechnicalError):
        await repository.update(entity_id, {"name": "New"})

    assert mock_db.rollback.called
