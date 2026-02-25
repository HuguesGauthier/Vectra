import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.connector_repository import ConnectorRepository
from app.models.connector import Connector, ConnectorStatus
from app.core.exceptions import TechnicalError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.connector_repository.select") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_delete():
    """Patch sqlalchemy delete."""
    with patch("app.repositories.connector_repository.delete") as mock:
        yield mock


@pytest.fixture
def connector_repo(mock_db):
    return ConnectorRepository(db=mock_db)


@pytest.mark.asyncio
async def test_get_all_with_stats_success(connector_repo, mock_db):
    """Test fetching connectors with stats aggregation."""
    # Mock connectors
    c1 = MagicMock(spec=Connector)
    c1.id = uuid4()
    c1.created_at = "date1"

    c2 = MagicMock(spec=Connector)
    c2.id = uuid4()
    c2.created_at = "date2"

    # Mock first query (Connectors)
    mock_result_connectors = MagicMock()
    mock_result_connectors.scalars.return_value.all.return_value = [c1, c2]

    # Mock second query (Stats)
    row1 = MagicMock()
    row1.connector_id = c1.id
    row1.max_vectorized_at = "2023-01-01"

    row2 = MagicMock()
    row2.connector_id = c2.id
    row2.max_vectorized_at = None

    mock_result_stats = MagicMock()
    # Async iterator for result
    mock_result_stats.__iter__.return_value = [row1, row2]

    # Configure db.execute to return different results for different calls
    mock_db.execute.side_effect = [mock_result_connectors, mock_result_stats]

    result = await connector_repo.get_all_with_stats(skip=0, limit=10)

    assert len(result) == 2
    assert result[0].last_vectorized_at == "2023-01-01"
    assert result[1].last_vectorized_at is None


@pytest.mark.asyncio
async def test_get_all_with_stats_empty(connector_repo, mock_db):
    """Test fetching connectors when none exist."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    result = await connector_repo.get_all_with_stats()

    assert result == []


@pytest.mark.asyncio
async def test_delete_with_relations_success(connector_repo, mock_db):
    """Test atomic deletion of connector and relations."""
    connector_id = uuid4()

    # Mock exists check
    with patch.object(connector_repo, "exists", return_value=True):
        # Mock deletion results
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        success = await connector_repo.delete_with_relations(connector_id)

        assert success is True
        # Verify 3 execute calls: 2 for relations, 1 for connector
        assert mock_db.execute.call_count == 3
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_with_relations_not_found(connector_repo, mock_db):
    """Test deletion of non-existent connector."""
    connector_id = uuid4()

    with patch.object(connector_repo, "exists", return_value=False):
        success = await connector_repo.delete_with_relations(connector_id)

        assert success is False
        mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_delete_with_relations_error(connector_repo, mock_db):
    """Test error handling during atomic deletion."""
    connector_id = uuid4()

    with patch.object(connector_repo, "exists", return_value=True):
        mock_db.execute.side_effect = SQLAlchemyError("DB Error")

        with pytest.raises(TechnicalError):
            await connector_repo.delete_with_relations(connector_id)

        mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_statuses(connector_repo, mock_db):
    """Test fetching connectors by status."""
    statuses = [ConnectorStatus.IDLE, ConnectorStatus.ERROR]

    mock_connectors = [MagicMock(), MagicMock()]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_connectors
    mock_db.execute.return_value = mock_result

    result = await connector_repo.get_by_statuses(statuses)

    assert len(result) == 2
