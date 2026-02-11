import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel
from app.repositories.base_repository import BaseRepository


# Mock schemas for testing
class MockCreateSchema(BaseModel):
    name: str
    description: str


class MockUpdateSchema(BaseModel):
    name: str = None
    description: str = None


# Mock model
class MockModel:
    __name__ = "MockModel"
    id: str
    name: str
    description: str

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.base_repository.select") as mock:
        yield mock


@pytest.fixture
def base_repo(mock_db):
    """Create a BaseRepository instance with mock db and model."""
    # We use a MagicMock for the model so it behaves like a mapped class for any other checks
    model_mock = MagicMock()
    model_mock.__name__ = "MockModel"
    return BaseRepository(model=model_mock, db=mock_db)


@pytest.mark.asyncio
async def test_get_success(base_repo, mock_db):
    """Test retrieving entity by ID."""
    entity_id = uuid4()

    mock_entity = MagicMock()
    mock_entity.id = entity_id
    mock_entity.name = "Test Entity"

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_entity
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await base_repo.get(entity_id)

    assert result is not None
    assert result.id == entity_id


@pytest.mark.asyncio
async def test_get_not_found(base_repo, mock_db):
    """Test retrieving non-existent entity."""
    entity_id = uuid4()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await base_repo.get(entity_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_error_handling(base_repo, mock_db):
    """Test error handling in get."""
    entity_id = uuid4()

    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    with pytest.raises(Exception):  # TechnicalError
        await base_repo.get(entity_id)


@pytest.mark.asyncio
async def test_get_all_success(base_repo, mock_db):
    """Test retrieving all entities with pagination."""
    mock_entities = [MagicMock(), MagicMock()]

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_entities
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await base_repo.get_all(skip=0, limit=10)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_all_max_limit(base_repo, mock_db):
    """Test that limit is capped at MAX_LIMIT (1000)."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    # Request more than MAX_LIMIT
    result = await base_repo.get_all(skip=0, limit=5000)

    # Should still work (limit capped internally)
    assert result == []


@pytest.mark.asyncio
async def test_create_success(base_repo, mock_db):
    """Test creating entity."""
    create_schema = MockCreateSchema(name="Test", description="Test description")

    mock_entity = MagicMock()
    mock_entity.id = uuid4()

    # Configure existing mock model to return the entity instance
    base_repo.model.return_value = mock_entity

    result = await base_repo.create(create_schema)

    # Verify commit and refresh were called
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_integrity_error(base_repo, mock_db):
    """Test integrity error handling during creation."""
    create_schema = MockCreateSchema(name="Test", description="Test description")

    mock_db.commit.side_effect = IntegrityError("statement", "params", "orig")

    # Configure existing mock model
    base_repo.model.return_value = MagicMock()

    with pytest.raises(Exception):  # ValidationError
        await base_repo.create(create_schema)

    # Verify rollback was called
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_success(base_repo, mock_db):
    """Test updating entity."""
    mock_entity = MagicMock()
    mock_entity.id = uuid4()
    mock_entity.name = "Old Name"

    update_schema = MockUpdateSchema(name="New Name")

    result = await base_repo.update(mock_entity, update_schema)

    # Verify commit and refresh were called
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_with_dict(base_repo, mock_db):
    """Test updating entity with dict."""
    mock_entity = MagicMock()
    mock_entity.id = uuid4()
    mock_entity.name = "Old Name"

    update_data = {"name": "New Name"}

    result = await base_repo.update(mock_entity, update_data)

    # Verify commit and refresh were called
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_rollback_on_error(base_repo, mock_db):
    """Test rollback on error during update."""
    mock_entity = MagicMock()
    update_schema = MockUpdateSchema(name="New Name")

    mock_db.commit.side_effect = SQLAlchemyError("Database error")

    with pytest.raises(Exception):  # TechnicalError
        await base_repo.update(mock_entity, update_schema)

    # Verify rollback was called
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_remove_success(base_repo, mock_db):
    """Test deleting entity."""
    entity_id = uuid4()
    mock_entity = MagicMock()
    mock_entity.id = entity_id

    # Mock get to return entity
    with patch.object(base_repo, "get", return_value=mock_entity):
        result = await base_repo.remove(entity_id)

        # Verify delete and commit were called
        mock_db.delete.assert_called_once_with(mock_entity)
        mock_db.commit.assert_called_once()
        assert result == mock_entity


@pytest.mark.asyncio
async def test_remove_not_found(base_repo, mock_db):
    """Test deleting non-existent entity."""
    entity_id = uuid4()

    # Mock get to return None
    with patch.object(base_repo, "get", return_value=None):
        result = await base_repo.remove(entity_id)

        # Should not call delete
        mock_db.delete.assert_not_called()
        assert result is None


@pytest.mark.asyncio
async def test_remove_rollback_on_error(base_repo, mock_db):
    """Test rollback on error during deletion."""
    entity_id = uuid4()
    mock_entity = MagicMock()

    with patch.object(base_repo, "get", return_value=mock_entity):
        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(Exception):  # TechnicalError
            await base_repo.remove(entity_id)

        # Verify rollback was called
        mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_count_success(base_repo, mock_db):
    """Test counting entities."""
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_db.execute.return_value = mock_result

    result = await base_repo.count()

    assert result == 42


@pytest.mark.asyncio
async def test_count_error_handling(base_repo, mock_db):
    """Test error handling in count."""
    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    with pytest.raises(Exception):  # TechnicalError
        await base_repo.count()


@pytest.mark.asyncio
async def test_exists_true(base_repo, mock_db):
    """Test checking if entity exists (true case)."""
    entity_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    mock_db.execute.return_value = mock_result

    result = await base_repo.exists(entity_id)

    assert result is True


@pytest.mark.asyncio
async def test_exists_false(base_repo, mock_db):
    """Test checking if entity exists (false case)."""
    entity_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_db.execute.return_value = mock_result

    result = await base_repo.exists(entity_id)

    assert result is False
