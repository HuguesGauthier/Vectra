import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
from fastapi import UploadFile
from app.services.assistant_service import AssistantService
from app.schemas.assistant import AssistantCreate, AssistantUpdate, AssistantResponse, AIModel
from app.core.exceptions import FunctionalError


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.fixture
def mock_trending():
    return AsyncMock()


@pytest.fixture
def service(mock_repo, mock_cache, mock_trending):
    return AssistantService(mock_repo, mock_cache, mock_trending)


def create_mock_assistant_model(assistant_id=None):
    """Helper to create a mock SQLAlchemy model for Assistant."""
    from datetime import datetime

    mock = MagicMock()
    mock.id = assistant_id or uuid4()
    mock.name = "Test Assistant"
    mock.description = "Description"
    mock.avatar_bg_color = "#FFFFFF"
    mock.avatar_text_color = "black"
    mock.avatar_image = None
    mock.avatar_vertical_position = 50
    mock.instructions = "Instructions"
    mock.model = AIModel.GEMINI
    mock.use_reranker = False
    mock.top_k_retrieval = 25
    mock.top_n_rerank = 5
    mock.retrieval_similarity_cutoff = 0.5
    mock.similarity_cutoff = 0.5
    mock.use_semantic_cache = False
    mock.cache_similarity_threshold = 0.9
    mock.cache_ttl_seconds = 3600
    mock.user_authentication = False
    mock.is_enabled = True
    mock.created_at = datetime.now()
    mock.updated_at = datetime.now()
    mock.linked_connectors = []

    # Configuration is a nested SQLModel/AssistantConfig
    mock.configuration = MagicMock()
    mock.configuration.temperature = 0.7
    mock.configuration.top_p = 1.0
    mock.configuration.presence_penalty = 0.0
    mock.configuration.frequency_penalty = 0.0
    mock.configuration.max_output_tokens = 4096
    mock.configuration.tags = []

    return mock


@pytest.mark.asyncio
async def test_create_assistant_success(service, mock_repo):
    # Setup
    data = AssistantCreate(
        name="Test Assistant", instructions="You are a test assistant.", avatar_bg_color="#FFFFFF"  # White background
    )
    mock_assistant = create_mock_assistant_model()
    mock_repo.create_with_connectors.return_value = mock_assistant

    # Execute
    result = await service.create_assistant(data)

    # Assert
    assert result.id == mock_assistant.id
    # HEX #FFFFFF (White) should result in "black" text
    assert data.avatar_text_color == "black"
    mock_repo.create_with_connectors.assert_called_once()


@pytest.mark.asyncio
async def test_upload_avatar_success(service, mock_repo):
    # Setup
    assistant_id = uuid4()
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "avatar.png"
    mock_file.content_type = "image/png"

    mock_assistant = create_mock_assistant_model(assistant_id)
    mock_repo.update_with_connectors.return_value = mock_assistant

    # Mock IO
    with patch.object(service, "_cleanup_avatar_file", AsyncMock()):
        with patch.object(service, "_save_file_async", AsyncMock()):
            # Execute
            result = await service.upload_avatar(assistant_id, mock_file)

            # Assert
            assert result.id == assistant_id
            mock_repo.update_with_connectors.assert_called_once()


@pytest.mark.asyncio
async def test_upload_avatar_invalid_type(service):
    # Setup
    assistant_id = uuid4()
    mock_file = MagicMock(spec=UploadFile)
    mock_file.content_type = "text/plain"

    # Execute & Assert
    with pytest.raises(FunctionalError, match="must be an image"):
        await service.upload_avatar(assistant_id, mock_file)


@pytest.mark.asyncio
async def test_delete_assistant_cleanup(service, mock_repo, mock_cache, mock_trending):
    # Setup
    assistant_id = uuid4()
    mock_repo.remove.return_value = True

    # Execute
    await service.delete_assistant(assistant_id)

    # Assert
    mock_cache.clear_assistant_cache.assert_called_once_with(str(assistant_id))
    mock_trending.delete_assistant_topics.assert_called_once_with(assistant_id)
    mock_repo.remove.assert_called_once_with(assistant_id)


@pytest.mark.asyncio
async def test_update_assistant_success(service, mock_repo):
    # Setup
    assistant_id = uuid4()
    data = AssistantUpdate(name="Updated Name", avatar_bg_color="#000000")  # Black background

    mock_assistant = create_mock_assistant_model(assistant_id)
    mock_repo.update_with_connectors.return_value = mock_assistant

    # Execute
    result = await service.update_assistant(assistant_id, data)

    # Assert
    assert result.id == assistant_id
    # HEX #000000 (Black) should result in "white" text
    assert data.avatar_text_color == "white"
    mock_repo.update_with_connectors.assert_called_once()
