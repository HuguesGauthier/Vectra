from unittest.mock import MagicMock, patch
import pytest
import os
from app.schemas.ingestion import FileIngestionConfig, WebIngestionConfig
from app.services.ingestion.connectors.file_connector import FileConnector
from app.services.ingestion.connectors.web_connector import WebConnector

@pytest.mark.asyncio
async def test_file_connector_validation_success():
    """Test FileConnector validates existing files correctly."""
    connector = FileConnector()
    valid_config = FileIngestionConfig(file_path="valid_path.txt")

    with patch("os.path.exists", return_value=True):
        assert await connector.validate_config(valid_config) is True


@pytest.mark.asyncio
async def test_web_connector_detects_ssrf():
    """Test WebConnector rejects localhost/private IPs."""
    connector = WebConnector()

    # Unsafe URLs
    assert await connector.validate_config(WebIngestionConfig(url="http://localhost:8080")) is False
    assert await connector.validate_config(WebIngestionConfig(url="http://127.0.0.1/admin")) is False

    # Safe URL
    assert await connector.validate_config(WebIngestionConfig(url="https://google.com")) is True


@pytest.mark.asyncio
async def test_file_connector_async_load():
    """Test FileConnector load_data runs async."""
    connector = FileConnector()
    config = FileIngestionConfig(file_path="test.txt")

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
