import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.ingestion_service import IngestionService


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_settings_service(mock_db_session):
    ss = MagicMock()
    ss.get_value = AsyncMock(return_value="fake_val")
    ss.load_cache = AsyncMock()
    return ss


@pytest.fixture
def mock_vector_service(mock_settings_service):
    vs = MagicMock()
    vs.get_collection_name = AsyncMock(return_value="test_collection")
    vs.get_async_qdrant_client = MagicMock()
    return vs


@pytest.fixture
def ingestion_service(mock_db_session, mock_vector_service, mock_settings_service):
    return IngestionService(
        db=mock_db_session, vector_service=mock_vector_service, settings_service=mock_settings_service
    )


@pytest.mark.asyncio
async def test_process_connector_nominal(ingestion_service, mock_db_session):
    """Test standard connector processing flow."""
    import app.services.ingestion_service as svc_mod
    from app.services.ingestion.ingestion_orchestrator import IngestionOrchestrator

    connector = MagicMock()
    connector.id = uuid4()
    connector.connector_type = "folder"
    connector.configuration = {"ai_provider": "gemini", "path": "/fake/path"}

    # Patch the instances on the service
    ingestion_service.connector_repo = AsyncMock()
    ingestion_service.connector_repo.get_by_id.return_value = connector
    ingestion_service.doc_repo = AsyncMock()
    ingestion_service.doc_repo.get_by_connector.return_value = []

    mock_orch = MagicMock()
    mock_orch.setup_pipeline = AsyncMock()
    mock_orch.setup_pipeline.return_value = ("p", "v", True, 1, "t")
    mock_orch.ingest_files = AsyncMock()

    with patch.object(svc_mod, "IngestionOrchestrator", return_value=mock_orch):
        with patch("app.services.ingestion_service.IngestionOrchestrator", return_value=mock_orch), \
             patch("app.services.ingestion_service.ConnectorFactory") as mock_factory:
            
            mock_factory.load_documents = AsyncMock(return_value=[])
            mock_scanner = mock_scanner_cls.return_value
            mock_scanner.__aenter__ = AsyncMock(return_value=mock_scanner)
            mock_scanner.__aexit__ = AsyncMock(return_value=None)
            mock_scanner.load_connector = AsyncMock(return_value=connector)
            mock_scanner.validate_path = MagicMock(return_value=True)
            mock_scanner.scan_connector_files = AsyncMock(return_value={})

            mock_scan_res = MagicMock()
            mock_scan_res.files_to_ingest = ["/fake/path.txt"]
            mock_scan_res.new_docs = []
            mock_scanner.identify_changed_files = AsyncMock(return_value=mock_scan_res)

            await ingestion_service.process_connector(connector.id)
            assert mock_orch.setup_pipeline.call_count == 1


@pytest.mark.asyncio
async def test_process_single_document_nominal(ingestion_service):
    """Test single document processing."""
    import app.services.ingestion_service as svc_mod
    from app.services.ingestion.ingestion_orchestrator import IngestionOrchestrator

    doc = MagicMock()
    doc.id = uuid4()
    doc.connector_id = uuid4()
    doc.file_path = "test.txt"

    connector = MagicMock()
    connector.id = doc.connector_id
    connector.connector_type = "file"
    connector.configuration = {"path": "/fake/", "ai_provider": "gemini"}

    # Patch the instances on the service
    ingestion_service.doc_repo = AsyncMock()
    ingestion_service.doc_repo.get_by_id.return_value = doc

    ingestion_service.connector_repo = AsyncMock()
    ingestion_service.connector_repo.get_by_id.return_value = connector

    async def mock_check_exists(*args, **kwargs):
        return True

    ingestion_service._check_file_exists = mock_check_exists

    mock_orch = MagicMock()
    mock_orch.setup_pipeline = AsyncMock()
    mock_orch.setup_pipeline.return_value = ("p", "v", True, 1, "t")
    mock_orch.ingest_files = AsyncMock()

    with patch.object(svc_mod, "IngestionOrchestrator", return_value=mock_orch):
        await ingestion_service.process_single_document(doc.id)
        assert mock_orch.setup_pipeline.call_count == 1
