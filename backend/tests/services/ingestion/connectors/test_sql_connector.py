import sys
from unittest.mock import MagicMock
import pytest

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.services.ingestion.connectors.sql_connector import SqlConnector
from app.schemas.ingestion import SqlIngestionConfig


@pytest.fixture
def connector():
    return SqlConnector()


@pytest.mark.asyncio
async def test_validate_config_success(connector):
    """Happy Path: validates a complete SQL configuration."""
    config = SqlIngestionConfig(host="localhost", port=1433, database="test_db", user="sa", password="secure_password")
    assert await connector.validate_config(config) is True


@pytest.mark.asyncio
async def test_validate_config_missing_field(connector):
    """Worst Case: raises ValueError when a required field is missing."""
    config = SqlIngestionConfig(
        host="localhost", port=1433, database="test_db", user="sa", password=""  # Missing password
    )
    with pytest.raises(ValueError, match="Missing required SQL configuration fields: password"):
        await connector.validate_config(config)


@pytest.mark.asyncio
async def test_load_data_returns_empty_list(connector):
    """Verify that load_data returns an empty list as it's a configuration connector."""
    config = SqlIngestionConfig(host="localhost", port=1433, database="test_db", user="sa", password="password")
    docs = await connector.load_data(config)
    assert isinstance(docs, list)
    assert len(docs) == 0
