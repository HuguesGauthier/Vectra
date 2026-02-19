"""
Unit tests for ChatEngineFactory.
"""

import pytest
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from app.factories.chat_engine_factory import ChatEngineFactory


class TestChatEngineFactory:
    """Test Chat Engine Factory."""

    @pytest.mark.asyncio
    @patch("app.factories.chat_engine_factory.LLMFactory")
    async def test_create_from_assistant(self, mock_llm_factory):
        """Should create LLM from assistant configuration."""
        # 1. Setup mocks
        mock_assistant = MagicMock()
        mock_assistant.model_provider = "openai"

        mock_settings = AsyncMock()

        def get_setting_value(key, default=None):
            if "chat_model" in key:
                return "gpt-4"
            if "api_key" in key:
                return "sk-test-key"
            return None

        mock_settings.get_value.side_effect = get_setting_value

        # 2. Run
        await ChatEngineFactory.create_from_assistant(mock_assistant, mock_settings, temperature=0.5)

        # 3. Verify
        mock_llm_factory.create_llm.assert_called_once_with(
            "openai", "gpt-4", "sk-test-key", temperature=0.5, top_k=ANY, base_url=None
        )


    @pytest.mark.asyncio
    @patch("app.factories.chat_engine_factory.LLMFactory")
    async def test_create_from_provider(self, mock_llm_factory):
        """Should create LLM from provider name directly."""
        # 1. Setup mocks
        mock_settings = AsyncMock()
        mock_settings.get_value.side_effect = lambda key: "gemini-pro" if "chat_model" in key else "genai-key"

        # 2. Run
        await ChatEngineFactory.create_from_provider("gemini", mock_settings)

        # 3. Verify
        mock_llm_factory.create_llm.assert_called_once_with(
            "gemini", "gemini-pro", "genai-key", temperature=ANY, top_k=ANY, base_url=None
        )

    @pytest.mark.asyncio
    @patch("app.factories.chat_engine_factory.LLMFactory")
    async def test_missing_config_warning(self, mock_llm_factory):
        """Should still call LLMFactory even if model name is missing (warning only)."""
        # 1. Setup mocks
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = None  # Everything missing

        # 2. Run
        await ChatEngineFactory.create_from_provider("mistral", mock_settings)

        # 3. Verify
        mock_llm_factory.create_llm.assert_called_once_with(
            "mistral", None, None, temperature=ANY, top_k=ANY, base_url=None
        )
