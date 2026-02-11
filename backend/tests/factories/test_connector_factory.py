import pytest
from app.factories.connector_factory import ConnectorFactory
from app.services.ingestion.connectors.file_connector import FileConnector
from app.services.ingestion.connectors.web_connector import WebConnector

@pytest.mark.asyncio
async def test_factory_creates_correct_instances():
    """Test Factory returns correct class types."""
    assert isinstance(ConnectorFactory.get_connector("file"), FileConnector)
    assert isinstance(ConnectorFactory.get_connector("web"), WebConnector)
    with pytest.raises(ValueError):
        ConnectorFactory.get_connector("invalid")
