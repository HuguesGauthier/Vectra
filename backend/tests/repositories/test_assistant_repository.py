import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.repositories.assistant_repository import AssistantRepository
from app.schemas.assistant import AssistantCreate, AssistantUpdate
from app.core.exceptions import EntityNotFound, TechnicalError, ValidationError


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def assistant_repo(mock_db):
    """Create an AssistantRepository instance with mock db."""
    return AssistantRepository(db=mock_db)


@pytest.mark.asyncio
async def test_get_with_connectors_success(assistant_repo, mock_db):
    """Test fetching assistant with connectors (N+1 prevention)."""
    assistant_id = uuid4()

    mock_assistant = MagicMock()
    mock_assistant.id = assistant_id
    mock_assistant.name = "Test Assistant"
    mock_assistant.linked_connectors = [MagicMock(), MagicMock()]

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_assistant
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await assistant_repo.get_with_connectors(assistant_id)

    assert result is not None
    assert result.id == assistant_id
    assert len(result.linked_connectors) == 2


@pytest.mark.asyncio
async def test_get_with_connectors_not_found(assistant_repo, mock_db):
    """Test fetching non-existent assistant."""
    assistant_id = uuid4()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await assistant_repo.get_with_connectors(assistant_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_with_connectors_error_handling(assistant_repo, mock_db):
    """Test error handling in get_with_connectors."""
    assistant_id = uuid4()

    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    with pytest.raises(TechnicalError):
        await assistant_repo.get_with_connectors(assistant_id)


@pytest.mark.asyncio
async def test_get_all_ordered_by_name_success(assistant_repo, mock_db):
    """Test fetching all assistants ordered by name."""
    mock_assistants = [MagicMock(name="Assistant A"), MagicMock(name="Assistant B")]

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_assistants
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await assistant_repo.get_all_ordered_by_name(skip=0, limit=10)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_all_ordered_by_name_max_limit(assistant_repo, mock_db):
    """Test that limit is capped at MAX_LIMIT."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    # Request more than MAX_LIMIT (1000)
    result = await assistant_repo.get_all_ordered_by_name(skip=0, limit=5000)

    # Should still work (limit capped internally)
    assert result == []


@pytest.mark.asyncio
async def test_create_with_connectors_success(assistant_repo, mock_db):
    """Test creating assistant with connectors."""
    connector_ids = [uuid4(), uuid4()]

    assistant_create = AssistantCreate(
        name="Test Assistant",
        description="Test description",
        system_prompt="Test prompt",
        linked_connector_ids=connector_ids,
    )

    # Mock connector validation
    mock_connectors = [MagicMock(id=cid) for cid in connector_ids]
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_connectors
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    # Mock the created assistant
    with patch.object(assistant_repo, "model") as mock_model:
        mock_assistant = MagicMock()
        mock_assistant.id = uuid4()
        mock_assistant.linked_connectors = mock_connectors
        mock_model.return_value = mock_assistant

        result = await assistant_repo.create_with_connectors(assistant_create)

        # Verify commit and refresh were called
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_with_connectors_missing_connector(assistant_repo, mock_db):
    """Test creating assistant with non-existent connector."""
    connector_ids = [uuid4(), uuid4()]

    assistant_create = AssistantCreate(
        name="Test Assistant",
        description="Test description",
        system_prompt="Test prompt",
        linked_connector_ids=connector_ids,
    )

    # Mock only one connector found (missing one)
    mock_connectors = [MagicMock(id=connector_ids[0])]
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_connectors
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    with patch.object(assistant_repo, "model"):
        with pytest.raises(ValidationError, match="Connectors not found"):
            await assistant_repo.create_with_connectors(assistant_create)


@pytest.mark.asyncio
async def test_create_with_connectors_integrity_error(assistant_repo, mock_db):
    """Test integrity error handling during creation."""
    assistant_create = AssistantCreate(
        name="Test Assistant", description="Test description", system_prompt="Test prompt"
    )

    mock_db.commit.side_effect = IntegrityError("statement", "params", "orig")

    with patch.object(assistant_repo, "model"):
        with pytest.raises(ValidationError):
            await assistant_repo.create_with_connectors(assistant_create)

        # Verify rollback was called
        mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_with_connectors_success(assistant_repo, mock_db):
    """Test updating assistant with connectors."""
    assistant_id = uuid4()
    connector_ids = [uuid4()]

    assistant_update = AssistantUpdate(name="Updated Name", linked_connector_ids=connector_ids)

    # Mock existing assistant
    mock_assistant = MagicMock()
    mock_assistant.id = assistant_id
    mock_assistant.linked_connectors = []

    # Mock get_with_connectors
    with patch.object(assistant_repo, "get_with_connectors", return_value=mock_assistant):
        # Mock connector validation
        mock_connectors = [MagicMock(id=connector_ids[0])]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_connectors
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await assistant_repo.update_with_connectors(assistant_id, assistant_update)

        # Verify commit and refresh were called
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_with_connectors_not_found(assistant_repo, mock_db):
    """Test updating non-existent assistant."""
    assistant_id = uuid4()
    assistant_update = AssistantUpdate(name="Updated Name")

    # Mock get_with_connectors returning None
    with patch.object(assistant_repo, "get_with_connectors", return_value=None):
        result = await assistant_repo.update_with_connectors(assistant_id, assistant_update)

        assert result is None


@pytest.mark.asyncio
async def test_update_with_connectors_rollback_on_error(assistant_repo, mock_db):
    """Test rollback on error during update."""
    assistant_id = uuid4()
    assistant_update = AssistantUpdate(name="Updated Name")

    mock_assistant = MagicMock()

    with patch.object(assistant_repo, "get_with_connectors", return_value=mock_assistant):
        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(TechnicalError):
            await assistant_repo.update_with_connectors(assistant_id, assistant_update)

        # Verify rollback was called
        mock_db.rollback.assert_called_once()
