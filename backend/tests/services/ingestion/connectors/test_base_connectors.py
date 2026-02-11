import sys
from unittest.mock import MagicMock, patch

# Mock problematic dependencies
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

import pytest
import os
from app.schemas.ingestion import FileIngestionConfig
from app.services.ingestion.connectors.file_connector import FileConnector


@pytest.mark.asyncio
async def test_file_connector_validation_success():
    """Test FileConnector validates existing files correctly."""
    connector = FileConnector()
    valid_config = FileIngestionConfig(path="valid_path.txt")

    with patch("os.path.exists", return_value=True):
        assert await connector.validate_config(valid_config) is True


@pytest.mark.asyncio
async def test_file_connector_async_load():
    """Test FileConnector load_data runs async."""
    connector = FileConnector()
    config = FileIngestionConfig(path="test.txt")

    mock_docs = [MagicMock()]

    with (
        patch("os.path.exists", return_value=True),
        patch("app.services.ingestion.connectors.file_connector.SimpleDirectoryReader") as MockReader,
    ):
        instance = MockReader.return_value
        instance.load_data.return_value = mock_docs

        result = await connector.load_data(config)
        assert result == mock_docs
        MockReader.assert_called_once()
