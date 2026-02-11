import sys
from unittest.mock import MagicMock, patch
import pytest
import os

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.services.ingestion.connectors.file_connector import FileConnector
from app.schemas.ingestion import FileIngestionConfig


@pytest.fixture
def connector():
    return FileConnector()


@pytest.mark.asyncio
async def test_validate_config_file_exists(connector):
    """Happy Path: validates an existing file."""
    config = FileIngestionConfig(path="existing_file.txt")
    with patch("os.path.isfile", return_value=True):
        assert await connector.validate_config(config) is True


@pytest.mark.asyncio
async def test_validate_config_is_directory(connector):
    """Worst Case: rejects a directory when a file is expected."""
    config = FileIngestionConfig(path="existing_dir")
    with patch("os.path.isfile", return_value=False):
        assert await connector.validate_config(config) is False


@pytest.mark.asyncio
async def test_load_data_special_format(connector):
    """Test handling of special formats (e.g., MP3)."""
    config = FileIngestionConfig(path="test.mp3")
    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", return_value=1234),
        patch("os.path.isabs", return_value=True),
    ):
        docs = await connector.load_data(config)
        assert len(docs) == 1
        assert docs[0].metadata["file_type"] == "mp3"
        assert docs[0].metadata["file_size"] == 1234


@pytest.mark.asyncio
async def test_load_data_file_not_found(connector):
    """Worst Case: error when file does not exist."""
    config = FileIngestionConfig(path="ghost.txt")
    with patch("os.path.isfile", return_value=False):
        with pytest.raises(ValueError, match="Invalid configuration or file not found"):
            await connector.load_data(config)


@pytest.mark.asyncio
async def test_load_data_generic_error(connector):
    """Test generic Exception wrapping."""
    config = FileIngestionConfig(path="error.txt")
    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.isabs", return_value=True),
        patch(
            "app.services.ingestion.connectors.file_connector.SimpleDirectoryReader",
            side_effect=Exception("Read Error"),
        ),
    ):
        with pytest.raises(RuntimeError, match="Failed to load file"):
            await connector.load_data(config)
