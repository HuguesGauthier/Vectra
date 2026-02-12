import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.factories.connector_factory import ConnectorFactory
from app.models.enums import ConnectorType
from app.services.ingestion.connectors.file_connector import FileConnector
from app.services.ingestion.connectors.folder_connector import FolderConnector
from app.services.ingestion.connectors.sql_connector import SqlConnector


@pytest.mark.asyncio
async def test_factory_creates_correct_instances():
    """Test Factory returns correct class types."""
    assert isinstance(ConnectorFactory.get_connector(ConnectorType.LOCAL_FILE), FileConnector)
    assert isinstance(ConnectorFactory.get_connector("local_file"), FileConnector)
    assert isinstance(ConnectorFactory.get_connector(ConnectorType.LOCAL_FOLDER), FolderConnector)
    assert isinstance(ConnectorFactory.get_connector(ConnectorType.SQL), SqlConnector)

    with pytest.raises(ValueError):
        ConnectorFactory.get_connector("invalid")


@pytest.mark.asyncio
async def test_load_documents_integration():
    """Test the full loading workflow with mocks."""
    # 1. Setup mock model
    mock_model = MagicMock()
    mock_model.connector_type = "local_file"
    mock_model.configuration = {"path": "/test/path"}

    # 2. Patch connector loading
    with MagicMock() as mock_connector:
        mock_connector.load_data = AsyncMock(return_value=["doc1"])

        with patch.object(ConnectorFactory, "get_connector", return_value=mock_connector):
            docs = await ConnectorFactory.load_documents(mock_model)

            assert docs == ["doc1"]
            mock_connector.load_data.assert_called_once()
