import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd
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
    return mock_session


@pytest.fixture
def mock_connector_repo():
    return AsyncMock()


@pytest.fixture
def mock_doc_repo():
    return AsyncMock()


@pytest.fixture
def ingestion_service(mock_db_session, mock_connector_repo, mock_doc_repo):
    service = IngestionService(mock_db_session)
    service.connector_repo = mock_connector_repo
    service.doc_repo = mock_doc_repo
    return service


@pytest.mark.asyncio
async def test_analyze_and_map_csv_success(ingestion_service, mock_connector_repo, mock_doc_repo):
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
    mock_connector.configuration = {"path": "/tmp"}

    mock_doc_repo.get_by_id.return_value = mock_doc
    mock_connector_repo.get_by_id.return_value = mock_connector

    # Mock Settings and LLM
    with (
        patch("app.services.settings_service.SettingsService.load_cache", new_callable=AsyncMock),
        patch(
            "app.services.settings_service.SettingsService.get_value", new_callable=AsyncMock, return_value="fake_key"
        ),
        patch("app.services.ingestion_service.IngestionService._check_file_exists", return_value=True),
        patch("pandas.read_csv") as mock_read_csv,
        patch("app.services.ingestion_service.GoogleGenAI") as MockLLM,
        patch("app.services.ingestion_service.manager.emit_document_update", new_callable=AsyncMock),
    ):

        # Setup Pandas
        mock_df = pd.DataFrame({"OldCol": [1, 2], "Desc": ["A", "B"]})
        mock_read_csv.return_value = mock_df

        # Setup LLM
        mock_llm_instance = MockLLM.return_value
        mock_response_obj = MagicMock()
        mock_response_obj.text = json.dumps(
            {
                "renaming_map": {"OldCol": "new_col", "Desc": "description"},
                "primary_id_col": "new_col",
                "payload_cols": ["new_col"],
                "content_cols": ["description"],
            }
        )
        mock_llm_instance.acomplete = AsyncMock(return_value=mock_response_obj)

        # Run
        await ingestion_service.analyze_and_map_csv(doc_id)

        # Verify
        mock_doc_repo.update.assert_called_once()
        update_args = mock_doc_repo.update.call_args[0][1]
        assert "file_metadata" in update_args
        assert update_args["file_metadata"]["ai_schema"]["renaming_map"]["OldCol"] == "new_col"
        assert update_args["status"] == DocStatus.INDEXING


@pytest.mark.asyncio
async def test_process_csv_data_success(ingestion_service, mock_connector_repo, mock_doc_repo):
    # Setup Mocks
    doc_id = uuid4()

    with patch("app.services.ingestion.orchestrator.IngestionOrchestrator", spec=True) as mock_orch_cls:
        mock_orch = mock_orch_cls.return_value
        mock_orch.ingest_csv_document = AsyncMock()

        # Run
        await ingestion_service.process_csv_data(doc_id)

        # Verify delegates to orchestrator
        mock_orch.ingest_csv_document.assert_called_once_with(doc_id)


