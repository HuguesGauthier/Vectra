import asyncio
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.core.exceptions import TechnicalError
from app.models.assistant import Assistant
from app.schemas.assistant import (AIModel, AssistantCreate, AssistantResponse,
                                   AssistantUpdate)
from app.services.assistant_service import AssistantService


# --- Fixtures ---

@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_cache_service():
    return AsyncMock()


@pytest.fixture
def mock_trending_service():
    return AsyncMock()


@pytest.fixture
def service(mock_repo, mock_cache_service, mock_trending_service):
    return AssistantService(
        assistant_repo=mock_repo,
        cache_service=mock_cache_service,
        trending_service=mock_trending_service
    )


@pytest.fixture
def sample_assistant():
    assistant_id = uuid4()
    return Assistant(
        id=assistant_id,
        name="Test Bot",
        model=AIModel.OPENAI,
        instructions="Test",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        linked_connectors=[],
        avatar_color="primary",
        avatar_text_color="white",
        use_reranker=False,
        top_k_retrieval=25,
        top_n_rerank=5,
        user_authentication=False,
        configuration={},
        is_enabled=True,
    )


@pytest.fixture
def sample_assistant_id():
    return uuid4()


# --- Tests ---

@pytest.mark.asyncio
class TestAssistantService:
    """Standard CRUD and basic logic tests."""

    async def test_get_assistants_success(self, service, mock_repo, sample_assistant):
        mock_repo.get_all_ordered_by_name.return_value = [sample_assistant]

        results = await service.get_assistants()

        assert len(results) == 1
        assert isinstance(results[0], AssistantResponse)
        assert results[0].name == "Test Bot"
        mock_repo.get_all_ordered_by_name.assert_awaited_once()

    async def test_get_assistant_found(self, service, mock_repo, sample_assistant):
        mock_repo.get.return_value = sample_assistant

        result = await service.get_assistant(sample_assistant.id)

        assert isinstance(result, AssistantResponse)
        assert result.id == sample_assistant.id
        mock_repo.get.assert_awaited_once_with(sample_assistant.id)

    async def test_get_assistant_not_found(self, service, mock_repo):
        mock_repo.get.return_value = None

        result = await service.get_assistant(uuid4())

        assert result is None

    async def test_create_assistant_success(self, service, mock_repo, sample_assistant):
        # Test contrast logic application during creation
        assistant_data = AssistantCreate(name="New Assist", avatar_bg_color="#000000")  # Black bg -> white text

        mock_repo.create_with_connectors.return_value = sample_assistant
        sample_assistant.name = "New Assist"

        await service.create_assistant(assistant_data)

        # Verify contrast logic modified the input data
        assert assistant_data.avatar_text_color == "white"
        mock_repo.create_with_connectors.assert_awaited_once_with(assistant_data)

    async def test_update_assistant_success(self, service, mock_repo, sample_assistant):
        assistant_id = sample_assistant.id
        update_data = AssistantUpdate(name="Updated", avatar_bg_color="#FFFFFF")  # White bg -> black text

        mock_repo.update_with_connectors.return_value = sample_assistant
        sample_assistant.name = "Updated"

        await service.update_assistant(assistant_id, update_data)

        # Verify contrast logic
        assert update_data.avatar_text_color == "black"
        mock_repo.update_with_connectors.assert_awaited_once_with(assistant_id, update_data)

    async def test_delete_assistant_success(self, service, mock_repo, sample_assistant_id):
        mock_repo.remove.return_value = True

        result = await service.delete_assistant(sample_assistant_id)

        assert result is True
        mock_repo.remove.assert_awaited_once_with(sample_assistant_id)

    async def test_service_error_handling(self, service, mock_repo):
        mock_repo.get_all_ordered_by_name.side_effect = Exception("Repo fail")

        with pytest.raises(TechnicalError) as exc:
            await service.get_assistants()

        assert "Failed to retrieve assistants" in str(exc.value)
        assert exc.value.error_code == "DB_ERROR"


@pytest.mark.asyncio
class TestAssistantServiceResilience:
    """Tests for system stability and edge case resilience."""

    async def test_delete_assistant_resilience_when_cache_fails(
        self, service, mock_repo, mock_cache_service, sample_assistant_id
    ):
        """
        P1: Ensures that if cache clearing fails (e.g. Redis down), the assistant is still deleted from DB.
        """
        # Arrange
        mock_repo.remove.return_value = True
        mock_cache_service.clear_assistant_cache.side_effect = Exception("Redis connection refused")

        # Act
        result = await service.delete_assistant(sample_assistant_id)

        # Assert
        assert result is True
        # Verify DB remove was called despite cache failure (Best Effort)
        mock_repo.remove.assert_called_once_with(sample_assistant_id)
        # Verify cache was attempted
        mock_cache_service.clear_assistant_cache.assert_called_once()

    async def test_delete_assistant_resilience_when_trending_fails(
        self, service, mock_repo, mock_trending_service, sample_assistant_id
    ):
        """P1: Resilience if trending service fails during deletion."""
        mock_repo.remove.return_value = True
        mock_trending_service.delete_assistant_topics.side_effect = Exception("Service Unavailable")

        result = await service.delete_assistant(sample_assistant_id)

        assert result is True
        mock_repo.remove.assert_called_once_with(sample_assistant_id)


@pytest.mark.asyncio
class TestAssistantServiceTechnicalAudit:
    """Audits for async efficiency and file management flows."""

    async def test_cleanup_avatar_is_non_blocking(self, service, sample_assistant_id):
        """
        P0: Verify that _cleanup_avatar_file offloads to executor.
        """
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # run_in_executor returns a future. In tests, we can return a resolved future.
            mock_future = asyncio.Future()
            mock_future.set_result(None)
            mock_loop.run_in_executor.return_value = mock_future

            await service._cleanup_avatar_file(sample_assistant_id)

            mock_loop.run_in_executor.assert_called_once()
            args, _ = mock_loop.run_in_executor.call_args
            assert args[0] is None
            assert callable(args[1])

    async def test_upload_avatar_flow(self, service, mock_repo, sample_assistant):
        """Verify the full flow of avatar upload."""
        assistant_id = sample_assistant.id
        file_mock = MagicMock(spec=UploadFile)
        file_mock.filename = "test.png"
        file_mock.content_type = "image/png"
        file_mock.file = MagicMock()

        # Mock internals
        service._cleanup_avatar_file = AsyncMock()
        service._save_file_async = AsyncMock()

        # Mock Repo update to return a valid Assistant model
        mock_repo.update_with_connectors.return_value = sample_assistant
        sample_assistant.avatar_image = f"{assistant_id}.png"

        result = await service.upload_avatar(assistant_id, file_mock)

        assert result.id == assistant_id
        assert result.avatar_image == f"{assistant_id}.png"
        # Verify orchestration
        service._cleanup_avatar_file.assert_awaited_with(assistant_id)
        service._save_file_async.assert_awaited()
        mock_repo.update_with_connectors.assert_called_once()
