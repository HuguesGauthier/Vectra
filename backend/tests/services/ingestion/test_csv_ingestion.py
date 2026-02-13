import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest

from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.enums import DocStatus
from app.services.ingestion_service import IngestionService


@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


@pytest.fixture
def mock_connector_repo():
    return AsyncMock()


@pytest.fixture
def mock_doc_repo():
    return AsyncMock()


@pytest.fixture
def mock_schema_service():
    return AsyncMock()


@pytest.fixture
def ingestion_service(mock_db_session, mock_connector_repo, mock_doc_repo, mock_schema_service):
    service = IngestionService(mock_db_session, schema_service=mock_schema_service)
    service.connector_repo = mock_connector_repo
    service.doc_repo = mock_doc_repo
    # Mock state_service to avoid unawaited coroutine warnings on finalize_connector
    service.state_service = AsyncMock()  # Must be AsyncMock to be awaited
    return service


@pytest.mark.asyncio
async def test_analyze_and_map_csv_delegation(ingestion_service, mock_schema_service):
    # Setup
    doc_id = uuid4()

    # Run
    await ingestion_service.analyze_and_map_csv(doc_id)

    # Verify delegation
    mock_schema_service.analyze_and_map_csv.assert_called_once_with(doc_id)


@pytest.mark.asyncio
async def test_process_single_document_csv_success(ingestion_service, mock_connector_repo, mock_doc_repo):
    # Setup Mocks
    doc_id = uuid4()
    connector_id = uuid4()

    mock_doc = MagicMock(spec=ConnectorDocument)
    mock_doc.id = doc_id
    mock_doc.connector_id = connector_id
    mock_doc.file_path = "test.csv"
    mock_doc.file_metadata = {}

    mock_connector = MagicMock(spec=Connector)
    mock_connector.id = connector_id
    mock_connector.connector_type = "local_file"
    mock_connector.configuration = {"path": "/tmp"}

    mock_doc_repo.get_by_id.return_value = mock_doc
    mock_connector_repo.get_by_id.return_value = mock_connector

    with (
        patch("app.services.settings_service.SettingsService.load_cache", new_callable=AsyncMock),
        patch.object(ingestion_service, "_file_exists", new_callable=AsyncMock, return_value=True),
        patch("app.core.interfaces.base_connector.get_full_path_from_connector", return_value="/tmp/test.csv"),
        patch.object(ingestion_service, "_get_or_create_orchestrator", new_callable=AsyncMock) as mock_get_orch,
        patch("app.services.ingestion_service.manager", new_callable=AsyncMock),
    ):
        mock_orch = MagicMock()
        mock_get_orch.return_value = mock_orch
        # setup_pipeline is called for all docs and returns 6 values
        mock_orch.setup_pipeline = AsyncMock(return_value=(MagicMock(), MagicMock(), 50, 5, MagicMock(), MagicMock()))
        mock_orch.ingest_csv_document = AsyncMock()

        # Run
        await ingestion_service.process_single_document(doc_id)

        # Verify delegates to orchestrator for CSV
        mock_orch.ingest_csv_document.assert_called_once_with(doc_id)
