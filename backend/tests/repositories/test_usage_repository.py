import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.usage_repository import UsageRepository
from app.models.usage_stat import UsageStat
from app.core.exceptions import TechnicalError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.usage_repository.select") as mock:
        yield mock


@pytest.fixture
def usage_repo(mock_db):
    return UsageRepository(db=mock_db)


@pytest.mark.asyncio
async def test_get_daily_usage(usage_repo, mock_db):
    """Test daily usage aggregation."""
    assistant_id = uuid4()

    # Mock result row objects
    row1 = MagicMock()
    row1.date = "2023-01-01"
    row1.count = 10
    row1.total_tokens = 1000
    row1.avg_duration = 5.0

    mock_result = MagicMock()
    mock_result.all.return_value = [row1]
    mock_db.execute.return_value = mock_result

    result = await usage_repo.get_daily_usage(assistant_id)

    assert len(result) == 1
    assert result[0]["date"] == "2023-01-01"
    assert result[0]["count"] == 10
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_total_tokens(usage_repo, mock_db):
    """Test total token summation."""
    assistant_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalar.return_value = 5000
    mock_db.execute.return_value = mock_result

    total = await usage_repo.get_total_tokens(assistant_id)

    assert total == 5000
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_total_tokens_empty(usage_repo, mock_db):
    """Test total tokens returning 0 when no data."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_db.execute.return_value = mock_result

    total = await usage_repo.get_total_tokens(uuid4())

    assert total == 0


@pytest.mark.asyncio
async def test_get_stats_by_user(usage_repo, mock_db):
    """Test fetching stats by user."""
    user_id = uuid4()
    mock_stat = MagicMock(spec=UsageStat)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_stat]
    mock_db.execute.return_value = mock_result

    result = await usage_repo.get_stats_by_user(user_id)

    assert len(result) == 1
    assert result[0] == mock_stat
