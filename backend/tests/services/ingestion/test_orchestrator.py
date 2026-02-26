from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import TechnicalError
from app.models.enums import ConnectorStatus, DocStatus
from app.services.ingestion.ingestion_orchestrator import IngestionOrchestrator, IngestionStoppedError


@pytest.fixture
def mock_dependencies():
    db = AsyncMock()
    vector_repo = AsyncMock()
    connector_repo = AsyncMock()
    doc_repo = AsyncMock()
    settings_service = AsyncMock()
    vector_service = AsyncMock()

    # Setup default mocks behavior
    vector_service.get_qdrant_client = MagicMock()
    vector_service.get_collection_name = AsyncMock(return_value="test_collection")
    vector_service.get_embedding_model = AsyncMock()

    return {
        "db": db,
        "vector_repo": vector_repo,
        "connector_repo": connector_repo,
        "doc_repo": doc_repo,
        "settings_service": settings_service,
        "vector_service": vector_service,
    }


@pytest.mark.asyncio
async def test_ingest_files_success(mock_dependencies):
    """Test successful ingestion of a file with stats emission."""
    orchestrator = IngestionOrchestrator(
        db=mock_dependencies["db"],
        vector_repo=mock_dependencies["vector_repo"],
        vector_service=mock_dependencies["vector_service"],
        settings_service=mock_dependencies["settings_service"],
    )
    # Inject mocked repos created inside __init__ usually, but we will refactor to allow injection or patching
    orchestrator.connector_repo = mock_dependencies["connector_repo"]
    orchestrator.doc_repo = mock_dependencies["doc_repo"]

    # Mock status check
    mock_dependencies["connector_repo"].get_by_id.return_value.status = ConnectorStatus.SYNCING

    # Mock document retrieval
    doc_id = uuid4()
    doc_mock = MagicMock()
    doc_mock.id = doc_id
    docs_map = {"test.pdf": doc_mock}

    # Mock Pipeline & TextSplitter
    # nodes for pipeline.arun return
    nodes = [MagicMock(get_content=lambda: "chunk"), MagicMock(get_content=lambda: "chunk")]
    for n in nodes:
        n.metadata = {"connector_document_id": str(doc_id)}

    pipeline = MagicMock()
    pipeline.arun = AsyncMock(return_value=nodes)
    text_splitter = MagicMock()
    # Mock splitting -> returns list of nodes
    text_splitter.get_nodes_from_documents.return_value = nodes

    # Mock IngestionFactory processing
    with patch("app.factories.ingestion_factory.IngestionFactory.get_processor") as mock_get_processor:
        processor_mock = AsyncMock()
        mock_get_processor.return_value = processor_mock
        # Return success document
        success_doc = MagicMock()
        success_doc.success = True
        success_doc.content = "Filtered content"
        success_doc.metadata = {}
        processor_mock.process.return_value = [success_doc]

        # Mock connection manager
        with patch("app.services.ingestion.ingestion_orchestrator.manager", new_callable=AsyncMock) as mock_manager:
            mock_manager.emit_document_update = AsyncMock()
            mock_manager.emit_document_progress = AsyncMock()
            mock_manager.emit_connector_progress = AsyncMock()

            await orchestrator.ingest_files(
                file_paths=["/tmp/test.pdf"],
                pipeline=pipeline,
                vector_store=MagicMock(),
                connector_id=uuid4(),
                connector_acl=[],
                ai_provider="gemini",
                batch_size=10,
                num_workers=1,
                docs_map=docs_map,
                text_splitter=text_splitter,
            )

            # Verify status update to INDEXED
            assert orchestrator.doc_repo.update.call_count >= 2
            # Verify stats emission
            mock_manager.emit_document_update.assert_called_with(
                str(doc_id),
                DocStatus.INDEXED,
                "Indexed 2 chunks",
                doc_token_count=10,  # 5 chars * 2? No, len("chunk")=5. Setup calls get_content.
                vector_point_count=2,
                last_vectorized_at=ANY,
                processing_duration_ms=ANY,
            )


@pytest.mark.asyncio
async def test_ingest_stopped_error(mock_dependencies):
    """Test ingestion interruption when connector is paused."""
    orchestrator = IngestionOrchestrator(
        db=mock_dependencies["db"],
        vector_repo=mock_dependencies["vector_repo"],
        vector_service=mock_dependencies["vector_service"],
        settings_service=mock_dependencies["settings_service"],
    )
    orchestrator.connector_repo = mock_dependencies["connector_repo"]

    # Mock PAUSED status
    mock_dependencies["connector_repo"].get_by_id.return_value.status = ConnectorStatus.PAUSED

    docs_map = {"test.pdf": MagicMock()}

    with pytest.raises(IngestionStoppedError):
        await orchestrator.ingest_files(
            file_paths=["/tmp/test.pdf"],
            pipeline=MagicMock(),
            vector_store=MagicMock(),
            connector_id=uuid4(),
            connector_acl=[],
            ai_provider="gemini",
            batch_size=10,
            num_workers=1,
            docs_map=docs_map,
        )
