from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConfigurationError, ExternalDependencyError, TechnicalError
from app.services.prompt_service import PromptService


@pytest.fixture
def mock_settings_service():
    return AsyncMock()


@pytest.fixture
def service(mock_settings_service):
    # Reset class cache for tests
    PromptService._CACHED_OPTIMIZER_PROMPT = None
    return PromptService(mock_settings_service)


@pytest.mark.asyncio
async def test_get_optimizer_prompt_success(service):
    """Verify that the prompt is loaded once and cached correctly using threads."""
    mock_content = "Refine this: {user_input}"

    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = mock_content

        # First call loads
        content1 = await service._get_optimizer_prompt()
        assert content1 == mock_content
        assert mock_thread.call_count == 1

        # Second call hits cache
        content2 = await service._get_optimizer_prompt()
        assert content2 == mock_content
        assert mock_thread.call_count == 1


@pytest.mark.asyncio
async def test_optimize_instruction_success(service, mock_settings_service):
    """Verify nominal flow: settings -> load prompt -> call Gemini."""
    mock_settings_service.get_value.side_effect = ["key_123", "gemini-pro"]

    with patch.object(PromptService, "_get_optimizer_prompt", new_callable=AsyncMock) as mock_load:
        # Prompt WITH split marker
        mock_load.return_value = "System System # INPUT User: {user_input}"

        with patch("app.services.prompt_service.LLMFactory.create_llm") as mock_create:
            mock_llm_inst = AsyncMock()
            # mock_llm_inst.achat returns a response object with message.content
            mock_response = MagicMock()
            mock_response.message.content = "Optimized instruction"
            mock_llm_inst.achat.return_value = mock_response
            mock_create.return_value = mock_llm_inst

            result = await service.optimize_instruction("test input")

            assert result == "Optimized instruction"
            assert mock_llm_inst.achat.called
            messages = mock_llm_inst.achat.call_args[0][0]
            assert len(messages) == 2
            assert messages[0].content == "System System"
            assert messages[1].content == "User: test input"


@pytest.mark.asyncio
async def test_optimize_instruction_fallback_no_marker(service, mock_settings_service):
    """Verify fallback when # INPUT is missing."""
    mock_settings_service.get_value.side_effect = ["key_123", "gemini-pro"]

    with patch.object(PromptService, "_get_optimizer_prompt", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = "Just system content"

        with patch("app.services.prompt_service.LLMFactory.create_llm") as mock_create:
            mock_llm_inst = AsyncMock()
            mock_response = MagicMock()
            mock_response.message.content = "Optimized"
            mock_llm_inst.achat.return_value = mock_response
            mock_create.return_value = mock_llm_inst

            await service.optimize_instruction("test input")

            messages = mock_llm_inst.achat.call_args[0][0]
            assert messages[0].content == "Just system content"
            assert "test input" in messages[1].content


@pytest.mark.asyncio
async def test_optimize_instruction_empty_input(service):
    """Verify TechnicalError on empty input."""
    with pytest.raises(TechnicalError) as exc:
        await service.optimize_instruction("")
    assert "user_input cannot be empty" in str(exc.value)


@pytest.mark.asyncio
async def test_optimize_instruction_truncation(service, mock_settings_service):
    """Verify input truncation for very long inputs."""
    mock_settings_service.get_value.side_effect = ["key_123", "gemini-pro"]
    long_input = "a" * 11000

    with patch.object(PromptService, "_get_optimizer_prompt", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = "# INPUT {user_input}"
        with patch("app.services.prompt_service.LLMFactory.create_llm") as mock_create:
            mock_llm_inst = AsyncMock()
            mock_llm_inst.achat.return_value = MagicMock(message=MagicMock(content="Reduced"))
            mock_create.return_value = mock_llm_inst

            await service.optimize_instruction(long_input)

            messages = mock_llm_inst.achat.call_args[0][0]
            assert len(messages[1].content) == 10000


@pytest.mark.asyncio
async def test_optimize_instruction_no_api_key(service, mock_settings_service):
    """Verify ConfigurationError when API key is missing."""
    mock_settings_service.get_value.return_value = None

    with pytest.raises(ConfigurationError) as exc:
        await service.optimize_instruction("test input")
    assert "No LLM provider is configured" in str(exc.value)


@pytest.mark.asyncio
async def test_optimize_instruction_api_error(service, mock_settings_service):
    """Verify mapping of external API errors."""
    mock_settings_service.get_value.side_effect = ["key_123", "gemini-pro"]

    with patch.object(PromptService, "_get_optimizer_prompt", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = "System: {user_input}"

        with patch("app.services.prompt_service.LLMFactory.create_llm") as mock_create:
            mock_llm_inst = AsyncMock()
            mock_llm_inst.achat.side_effect = Exception("API Quota exceeded")
            mock_create.return_value = mock_llm_inst

            with pytest.raises(ExternalDependencyError):
                await service.optimize_instruction("test input")
