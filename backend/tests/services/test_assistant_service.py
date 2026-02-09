from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.assistant import Assistant
from app.schemas.assistant import (AIModel, AssistantCreate, AssistantResponse,
                                   AssistantUpdate)
from app.services.assistant_service import AssistantService, TechnicalError


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    return AssistantService(mock_repo)


@pytest.fixture
def sample_assistant():
    assistant_id = uuid4()
    return Assistant(
        id=assistant_id,
        name="Test Bot",
        model=AIModel.GPT_4O,
        instructions="Test",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        linked_connectors=[],
        # Default fields required for Pydantic validation if not defaulted by SQLModel init in test context
        avatar_color="primary",
        avatar_text_color="white",
        use_reranker=False,
        top_k_retrieval=25,
        top_n_rerank=5,
        user_authentication=False,
        configuration={},
        is_enabled=True,
    )


@pytest.mark.asyncio
class TestAssistantService:

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
        assistant_data = AssistantCreate(name="New Assist", avatar_color="#000000")  # Black bg -> White text

        # Repository receives the data with updated avatar_text_color
        mock_repo.create_with_connectors.return_value = sample_assistant
        sample_assistant.name = "New Assist"
        sample_assistant.avatar_text_color = "white"

        result = await service.create_assistant(assistant_data)

        assert isinstance(result, AssistantResponse)
        assert assistant_data.avatar_text_color == "white"
        mock_repo.create_with_connectors.assert_awaited_once_with(assistant_data)

    async def test_update_assistant_success(self, service, mock_repo, sample_assistant):
        assistant_id = sample_assistant.id
        update_data = AssistantUpdate(name="Updated", avatar_color="#FFFFFF")  # White bg -> Black text

        mock_repo.update_with_connectors.return_value = sample_assistant
        sample_assistant.name = "Updated"
        sample_assistant.avatar_color = "#FFFFFF"
        sample_assistant.avatar_text_color = "black"

        result = await service.update_assistant(assistant_id, update_data)

        assert isinstance(result, AssistantResponse)
        assert result.name == "Updated"
        assert update_data.avatar_text_color == "black"
        mock_repo.update_with_connectors.assert_awaited_once_with(assistant_id, update_data)

    async def test_delete_assistant_success(self, service, mock_repo):
        assistant_id = uuid4()
        mock_repo.remove.return_value = True

        result = await service.delete_assistant(assistant_id)

        assert result is True
        mock_repo.remove.assert_awaited_once_with(assistant_id)

    async def test_service_error_handling(self, service, mock_repo):
        mock_repo.get_all_ordered_by_name.side_effect = Exception("Repo fail")

        with pytest.raises(TechnicalError) as exc:
            await service.get_assistants()

        assert "Failed to retrieve assistants" in str(exc.value)
        assert exc.value.error_code == "DB_ERROR"
