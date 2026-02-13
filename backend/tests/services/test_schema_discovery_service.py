import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path

from app.services.schema_discovery_service import SchemaDiscoveryService, TransientIngestionError
from app.core.exceptions import ConfigurationError, EntityNotFound, TechnicalError
from app.models.enums import DocStatus


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    service = AsyncMock()
    service.get_value.return_value = "mock-value"
    service.load_cache = AsyncMock()
    return service


@pytest.fixture
def mock_state():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_settings, mock_state):
    return SchemaDiscoveryService(mock_db, mock_settings, mock_state)


@pytest.mark.asyncio
async def test_analyze_and_map_csv_success(service, mock_db, mock_settings, mock_state):
    # Setup
    doc_id = uuid4()
    connector_id = uuid4()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.connector_id = connector_id
    mock_doc.file_path = "test.csv"
    mock_doc.file_metadata = {}

    service.doc_repo.get_by_id = AsyncMock(return_value=mock_doc)
    service.connector_repo.get_by_id = AsyncMock(return_value=MagicMock())
    service.doc_repo.update = AsyncMock()

    # Mock file operations
    with patch("app.services.schema_discovery_service.aiofiles.open", MagicMock()):
        with patch.object(SchemaDiscoveryService, "_validate_csv_file", AsyncMock()):
            with patch.object(SchemaDiscoveryService, "_read_csv_preview", AsyncMock(return_value="h1,h2\nv1,v2")):

                # Mock LLM call
                mock_schema = {"renaming_map": {"h1": "col1"}, "semantic_cols": ["col1"]}
                with patch.object(
                    SchemaDiscoveryService, "_discover_schema_with_llm", AsyncMock(return_value=mock_schema)
                ):

                    # Execute
                    await service.analyze_and_map_csv(doc_id)

                    # Assert
                    service.doc_repo.update.assert_called_once()
                    args = service.doc_repo.update.call_args[0][1]
                    assert args["status"] == DocStatus.INDEXING
                    assert args["file_metadata"]["ai_schema"] == mock_schema
                    mock_state.update_document_status.assert_called_once()


@pytest.mark.asyncio
async def test_llm_retry_on_timeout(service, mock_settings):
    # Setup
    api_key = "test-key"
    csv_preview = "h1,h2"
    mock_settings.get_value.return_value = "gemini-model"

    # Mock LLM to fail once then succeed
    mock_llm = MagicMock()
    mock_llm.acomplete = AsyncMock()

    # We need to mock the LLM creation in the method
    with patch("app.factories.llm_factory.LLMFactory.create_llm", return_value=mock_llm):
        # First call times out, second succeeds
        mock_response = MagicMock()
        mock_response.text = '{"renaming_map": {}, "semantic_cols": []}'

        # side_effect for acomplete
        mock_llm.acomplete.side_effect = [asyncio.TimeoutError("Timeout"), mock_response]

        # Execute
        result = await service._discover_schema_with_llm(api_key, csv_preview)

        # Assert
        assert result["renaming_map"] == {}
        assert mock_llm.acomplete.call_count == 2


@pytest.mark.asyncio
async def test_invalid_llm_response_handling(service):
    # Setup
    invalid_text = "Not a JSON"

    # Execute & Assert
    with pytest.raises(TechnicalError, match="Failed to parse LLM response"):
        service._parse_llm_response(invalid_text)


@pytest.mark.asyncio
async def test_missing_keys_in_llm_response(service):
    # Setup
    incomplete_json = '{"only_one_key": []}'

    # Execute & Assert
    with pytest.raises(TechnicalError, match="missing required keys"):
        service._parse_llm_response(incomplete_json)


@pytest.mark.asyncio
async def test_analyze_and_map_csv_entity_not_found(service, mock_db, mock_state):
    # Setup
    doc_id = uuid4()
    service.doc_repo.get_by_id = AsyncMock(return_value=None)

    # Execute & Assert
    with pytest.raises(EntityNotFound):
        await service.analyze_and_map_csv(doc_id)

    mock_state.mark_document_failed.assert_not_called()  # Because doc was not found, no doc.id to call it with (per current logic) or it fails early.
    # Wait, the current logic only calls it if "doc" in locals(). Since get_by_id returns None, it might raise before doc is in locals or if it is None.
    # In my refactor, doc = None is at top. If get_by_id returns None, doc is None.
