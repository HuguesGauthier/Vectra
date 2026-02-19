"""
Unit tests for LLMFactory.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.factories.llm_factory import LLMFactory
from app.core.exceptions import ConfigurationError


class TestLLMFactory:
    """Test LLM Factory."""

    @pytest.fixture(autouse=True)
    def mock_llms(self):
        """Mock all llama_index models to avoid persistent AttributeError on patching."""
        mock_google = MagicMock()
        mock_openai = MagicMock()
        mock_mistral = MagicMock()
        mock_ollama = MagicMock()
        mock_openailike = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "llama_index.llms.google_genai": mock_google,
                "llama_index.llms.openai": mock_openai,
                "llama_index.llms.mistralai": mock_mistral,
                "llama_index.llms.ollama": mock_ollama,
                "llama_index.llms.openai_like": mock_openailike,
            },
        ):
            self.mock_google_class = mock_google.GoogleGenAI
            self.mock_openai_class = mock_openai.OpenAI
            self.mock_mistral_class = mock_mistral.MistralAI
            self.mock_ollama_class = mock_ollama.Ollama
            self.mock_openailike_class = mock_openailike.OpenAILike
            yield

    @pytest.mark.asyncio
    async def test_create_gemini_success(self):
        """Should create GoogleGenAI instance with models/ prefix."""
        llm = LLMFactory.create_llm(
            provider="gemini", model_name="gemini-1.5-flash", api_key="test-key", temperature=0.5, top_k=20
        )

        self.mock_google_class.assert_called_once_with(
            model="models/gemini-1.5-flash", api_key="test-key", temperature=0.5, top_k=20
        )
        assert llm == self.mock_google_class.return_value

    @pytest.mark.asyncio
    async def test_create_openai_success(self):
        """Should create OpenAI instance with stream_options."""
        llm = LLMFactory.create_llm(provider="openai", model_name="gpt-4", api_key="test-key")

        self.mock_openai_class.assert_called_once()
        args, kwargs = self.mock_openai_class.call_args
        assert kwargs["model"] == "gpt-4"
        assert kwargs["api_key"] == "test-key"
        assert kwargs["additional_kwargs"] == {"stream_options": {"include_usage": True}}
        assert llm == self.mock_openai_class.return_value

    @pytest.mark.asyncio
    async def test_create_mistral_success(self):
        """Should create MistralAI instance."""
        llm = LLMFactory.create_llm(provider="mistral", model_name="mistral-large", api_key="test-key")

        self.mock_mistral_class.assert_called_once_with(model="mistral-large", api_key="test-key", temperature=0.7)
        assert llm == self.mock_mistral_class.return_value

    @pytest.mark.asyncio
    async def test_create_ollama_success(self):
        """Should create Ollama instance with default base_url."""
        llm = LLMFactory.create_llm(provider="ollama", model_name="llama3", api_key="", temperature=0.7, top_k=10)

        self.mock_ollama_class.assert_called_once_with(
            model="llama3",
            base_url="http://localhost:11434",
            temperature=0.7,
            additional_kwargs={"top_k": 10},
            request_timeout=360.0,
        )

    @pytest.mark.asyncio
    async def test_create_local_success(self):
        """Should create OpenAILike instance for local provider."""
        llm = LLMFactory.create_llm(provider="local", model_name="custom-model", api_key=None)

        self.mock_openailike_class.assert_called_once_with(
            model="custom-model",
            api_key="not-needed",
            api_base="http://localhost:1234/v1",
            temperature=0.7,
            is_chat_model=True,
        )

    def test_missing_api_key_raises_error(self):
        """Should raise ConfigurationError if API key is missing for cloud providers."""
        with pytest.raises(ConfigurationError) as exc:
            LLMFactory.create_llm(provider="openai", model_name="gpt-4", api_key="")

        assert "API Key missing" in str(exc.value)

    def test_unsupported_provider_raises_error(self):
        """Should raise ConfigurationError for unknown provider."""
        with pytest.raises(ConfigurationError) as exc:
            LLMFactory.create_llm(provider="unknown", model_name="model", api_key="key")

        assert "Unsupported LLM provider" in str(exc.value)

    @pytest.mark.asyncio
    async def test_structured_llm_support(self):
        """Should call as_structured_llm if output_class is provided."""

        class MockOutput:
            pass

        mock_llm_instance = self.mock_openai_class.return_value
        mock_llm_instance.as_structured_llm = MagicMock()

        LLMFactory.create_llm(provider="openai", model_name="gpt-4", api_key="key", output_class=MockOutput)

        mock_llm_instance.as_structured_llm.assert_called_once_with(MockOutput)
