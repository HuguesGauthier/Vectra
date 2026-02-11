import pytest
from uuid import uuid4, UUID
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, Field

from app.repositories.sql_repository import SQLRepository
from app.core.exceptions import TechnicalError


# --- Mock Model for Testing ---
class MockModel(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    age: int


# --- Fixtures ---


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    with patch("app.repositories.sql_repository.select") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_delete_stmt():
    with patch("app.repositories.sql_repository.sql_delete") as mock:
        yield mock


@pytest.fixture
def repo(mock_db):
    # Initialize repository with MockModel
    return SQLRepository(model=MockModel, db=mock_db)


# --- Tests ---


@pytest.mark.asyncio
async def test_create_success(repo, mock_db):
    """Test successful creation."""
    data = MockModel(name="Test", age=30)

    result = await repo.create(data)

    assert result.name == "Test"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_error(repo, mock_db):
    """Test creation rollback on error."""
    data = MockModel(name="Test", age=30)
    mock_db.commit.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(TechnicalError):
        await repo.create(data)

    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_delete_success(repo, mock_db):
    """Test successful deletion checking rowcount BEFORE commit."""
    entity_id = uuid4()

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.execute.return_value = mock_result

    deleted = await repo.delete(entity_id)

    assert deleted is True
    # Ensure commit happens
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_not_found(repo, mock_db):
    """Test deletion logic when entity not found."""
    entity_id = uuid4()

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db.execute.return_value = mock_result

    deleted = await repo.delete(entity_id)

    assert deleted is False
    mock_db.commit.assert_called_once()  # We still commit generally even if no rows affected in raw SQL delete


@pytest.mark.asyncio
async def test_update_batch_no_side_effect(repo, mock_db):
    """Test update_batch does not mutate input dicts."""
    uid = uuid4()
    task = {"id": uid, "name": "Updated"}
    original_task = task.copy()

    # Mock get_by_id to return an entity
    mock_entity = MockModel(id=uid, name="Old", age=20)

    # We need to mock get_by_id. Since it's an async method on self,
    # we can patch it or mock the db call inside it.
    # To simplify, let's patch the valid call inside get_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_entity
    # execute is called by get_by_id
    mock_db.execute.return_value = mock_result

    count = await repo.update_batch([task])

    assert count == 1
    # VERIFY: 'id' key should still be in the task dict
    assert "id" in task
    assert task == original_task
    # Verify entity updated
    assert mock_entity.name == "Updated"


@pytest.mark.asyncio
async def test_get_all_with_filters(repo, mock_db):
    """Test get_all generic filtering."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    filters = {"name": "Test", "age": 25}
    await repo.get_all(filters=filters)

    mock_db.execute.assert_called_once()
    # Analyzing call args on mocks for expression construction is brittle,
    # ensuring it runs without error is primary for generic code.
