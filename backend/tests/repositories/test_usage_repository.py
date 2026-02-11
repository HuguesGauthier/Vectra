from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4
import pytest
from app.repositories.usage_repository import UsageRepository

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_usage_repository_daily(mock_db):
    """Test get_daily_usage SQL construction and execution."""
    repo = UsageRepository(mock_db)

    # Create a synchronous Mock for the Result object
    mock_result = MagicMock()
    mock_result.all.return_value = [MagicMock(date="2023-01-01", count=10, total_tokens=100, avg_duration=5.0)]
    # Ensure await db.execute() returns this synchronous mock
    mock_db.execute.return_value = mock_result

    result = await repo.get_daily_usage(uuid4(), days=7)

    assert len(result) == 1
    assert result[0]["count"] == 10
    mock_db.execute.assert_called_once()
