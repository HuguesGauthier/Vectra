import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.ingestion.ingestion_orchestrator import IngestionOrchestrator
from app.models.enums import DocStatus, ConnectorStatus


@pytest.mark.asyncio
async def test_ingest_files_propagates_provider():
    """Verify that ingest_files correctly passes ai_provider to processors."""
    # Mock dependencies
    db = AsyncMock()
    vector_repo = MagicMock()
    settings_service = AsyncMock()
    vector_service = AsyncMock()

    orchestrator = IngestionOrchestrator(db, vector_repo, settings_service, vector_service)

    # Mock repositories on the orchestrator
    orchestrator.connector_repo = AsyncMock()
    orchestrator.doc_repo = AsyncMock()

    # Mock status check - need a mock connector object with a status
    mock_connector = MagicMock()
    mock_connector.status = ConnectorStatus.SYNCING
    orchestrator.connector_repo.get_by_id = AsyncMock(return_value=mock_connector)

    # Mock pipeline and other arguments
    pipeline = MagicMock()
    pipeline.arun = AsyncMock(return_value=[])
    vector_store = MagicMock()
    connector_id = uuid4()
    ai_provider = "gemini"

    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.file_path = "test.jpg"

    abs_path = Path("abs/path/test.jpg").resolve()
    file_paths = [(str(abs_path), "test.jpg")]
    docs_map = {"test.jpg": mock_doc}

    # Mock IngestionFactory and Processor
    mock_processor = AsyncMock()
    mock_processor.process.return_value = []

    with patch(
        "app.services.ingestion.ingestion_orchestrator.IngestionFactory.get_processor", return_value=mock_processor
    ):
        with patch("app.services.ingestion.ingestion_orchestrator.manager.emit_document_update", AsyncMock()):
            with patch("app.services.ingestion.ingestion_orchestrator.manager.emit_connector_progress", AsyncMock()):
                await orchestrator.ingest_files(
                    file_paths=file_paths,
                    pipeline=pipeline,
                    vector_store=vector_store,
                    connector_id=connector_id,
                    connector_acl=[],
                    ai_provider=ai_provider,
                    batch_size=10,
                    num_workers=0,
                    docs_map=docs_map,
                )

    # Verify processor.process call
    assert mock_processor.process.called
    args, kwargs = mock_processor.process.call_args
    # Compare paths after resolving both to handle Windows drive casing
    assert Path(args[0]).resolve() == abs_path.resolve()
    assert kwargs["ai_provider"] == ai_provider


@pytest.mark.asyncio
async def test_image_processor_respects_provider():
    """Verify that ImageProcessor prioritizes the passed provider."""
    from app.factories.processors.image_processor import ImageProcessor

    processor = ImageProcessor()

    # Mock _validate_file_path to return a mock path
    mock_path = MagicMock(spec=Path)
    mock_path.name = "test.png"
    mock_path.stat.return_value.st_size = 100
    mock_path.__str__.return_value = "test.png"
    processor._validate_file_path = AsyncMock(return_value=mock_path)

    # Patch get_session_factory WHERE IT IS USED
    with patch("app.factories.processors.image_processor.get_session_factory") as mock_get_factory:
        mock_factory = MagicMock()
        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_get_factory.return_value = mock_factory

        # Patch SettingsService and others where they are imported in the target module
        with patch("app.factories.processors.image_processor.SettingsService") as mock_settings_service_cls:
            mock_settings_service = mock_settings_service_cls.return_value

            # Test Case 1: Provider is NOT gemini -> should skip
            result = await processor.process("test.png", ai_provider="ollama")
            assert result == []

            # Test Case 2: Provider is None -> check settings
            mock_settings_service.get_value = AsyncMock(return_value="gemini")
            with patch("app.factories.processors.image_processor.get_gemini_client", AsyncMock()):
                with patch("app.factories.processors.image_processor.GeminiVisionService") as mock_vision_svc:
                    mock_vision_svc.return_value.analyze_image = AsyncMock(return_value="desc")
                    result = await processor.process("test.png", ai_provider=None)
                    assert len(result) == 1
                    assert result[0].content == "desc"
                    mock_settings_service.get_value.assert_awaited_with("embedding_provider")


@pytest.mark.asyncio
async def test_audio_processor_respects_provider():
    """Verify that AudioProcessor prioritizes the passed provider."""
    from app.factories.processors.audio_processor import AudioProcessor

    processor = AudioProcessor()

    # Mock _validate_file_path to return a mock path
    mock_path = MagicMock(spec=Path)
    mock_path.name = "test.mp3"
    mock_path.stat.return_value.st_size = 1024
    mock_path.__str__.return_value = "test.mp3"
    processor._validate_file_path = AsyncMock(return_value=mock_path)

    # Patch get_session_factory WHERE IT IS USED
    with patch("app.factories.processors.audio_processor.get_session_factory") as mock_get_factory:
        mock_factory = MagicMock()
        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_get_factory.return_value = mock_factory

        # Patch SettingsService
        with patch("app.factories.processors.audio_processor.SettingsService") as mock_settings_service_cls:
            mock_settings_service = mock_settings_service_cls.return_value

            # Test Case 1: Provider is gemini
            mock_settings_service.get_value = AsyncMock(return_value="gemini")
            with patch("app.factories.processors.audio_processor.get_gemini_client", AsyncMock()):
                with patch("app.factories.processors.audio_processor.GeminiAudioService") as mock_audio_svc:
                    # Mock transcription return (Mock Response model mimicry)
                    mock_chunk = MagicMock()
                    mock_chunk.text = "transcription"
                    mock_chunk.speaker = "Speaker 1"
                    mock_chunk.timestamp_start = "00:00"
                    mock_audio_svc.return_value.transcribe_file = AsyncMock(return_value=[mock_chunk])

                    result = await processor.process("test.mp3", ai_provider="gemini")
                    assert len(result) == 1
                    assert "Speaker 1: transcription" in result[0].content
                    assert result[0].metadata["source_type"] == "audio"
