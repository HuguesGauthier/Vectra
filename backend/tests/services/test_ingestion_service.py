import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.ingestion_service import IngestionService, IngestionStoppedError
from app.models.enums import ConnectorStatus, DocStatus
from app.core.exceptions import EntityNotFound, ConfigurationError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_orchestrator():
    orch = AsyncMock()
    orch.setup_pipeline.return_value = (MagicMock(), MagicMock(), 50, 5, MagicMock(), MagicMock())
    return orch


@pytest.fixture
def ingestion_service(mock_db):
    service = IngestionService(db=mock_db)
    service.connector_repo = AsyncMock()
    service.doc_repo = AsyncMock()
    service.state_service = AsyncMock()
    service.settings_service = AsyncMock()
    service.vector_service = AsyncMock()
    service.schema_service = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_process_connector_happy_path(ingestion_service, mock_orchestrator):
    # Setup
    connector_id = uuid4()
    connector = MagicMock()
    connector.id = connector_id
    connector.connector_type = "local_folder"
    connector.configuration = {}

    ingestion_service.connector_repo.get_by_id.return_value = connector
    ingestion_service.doc_repo.upsert_connector_documents.return_value = []

    with (
        patch.object(ingestion_service, "_get_or_create_orchestrator", return_value=mock_orchestrator),
        patch("app.factories.connector_factory.ConnectorFactory.load_documents", return_value=[]),
    ):

        # Execute
        await ingestion_service.process_connector(connector_id)

        # Verify
        ingestion_service.state_service.update_connector_status.assert_called_with(
            connector_id, ConnectorStatus.VECTORIZING
        )
        ingestion_service.state_service.finalize_connector.assert_called_with(connector_id)


@pytest.mark.asyncio
async def test_process_connector_not_found(ingestion_service):
    # Setup
    connector_id = uuid4()
    ingestion_service.connector_repo.get_by_id.return_value = None

    # Execute
    await ingestion_service.process_connector(connector_id)

    # Verify
    ingestion_service.state_service.update_connector_status.assert_not_called()


@pytest.mark.asyncio
async def test_process_connector_error_handling(ingestion_service):
    # Setup
    connector_id = uuid4()
    connector = MagicMock()
    connector.id = connector_id
    connector.connector_type = "local_folder"

    ingestion_service.connector_repo.get_by_id.return_value = connector
    ingestion_service.settings_service.load_cache.side_effect = Exception("Crashes!")

    # Execute
    with pytest.raises(Exception):
        await ingestion_service.process_connector(connector_id)

    # Verify
    ingestion_service.state_service.mark_connector_failed.assert_called_once()
    assert ingestion_service.db.rollback.called


@pytest.mark.asyncio
async def test_process_single_document_happy_path(ingestion_service, mock_orchestrator):
    # Setup
    doc_id = uuid4()
    doc = MagicMock()
    doc.id = doc_id
    doc.connector_id = uuid4()
    doc.file_path = "test.txt"

    connector = MagicMock()
    connector.id = doc.connector_id
    connector.connector_type = "local_file"

    ingestion_service.doc_repo.get_by_id.return_value = doc
    ingestion_service.connector_repo.get_by_id.return_value = connector
    ingestion_service._file_exists = AsyncMock(return_value=True)

    with patch.object(ingestion_service, "_get_or_create_orchestrator", return_value=mock_orchestrator):
        # Execute
        await ingestion_service.process_single_document(doc_id)

        # Verify
        ingestion_service.state_service.update_document_status.assert_called()
        ingestion_service.state_service.finalize_connector.assert_called()


@pytest.mark.asyncio
async def test_is_sql_connector(ingestion_service):
    connector = MagicMock()

    connector.connector_type = "sql"
    assert ingestion_service._is_sql_connector(connector) is True

    connector.connector_type = "VANNA_SQL"
    assert ingestion_service._is_sql_connector(connector) is True

    connector.connector_type = "local_file"
    assert ingestion_service._is_sql_connector(connector) is False
