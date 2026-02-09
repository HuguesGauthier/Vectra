import json
import sys
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.exceptions import ConfigurationError, ExternalDependencyError
from app.core.settings import settings
from app.services.chat_service import ChatService, LLMFactory
from app.services.settings_service import SettingsService
from app.services.vector_service import VectorService

# --- Fixtures ---


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def assistant_mock():
    assistant = MagicMock()
    assistant.id = "123"
    assistant.model = "gemini-1.5-flash"
    assistant.model = "gemini-1.5-flash"
    # Fix: configuration should be an object (Pydantic-like), not a dict, to match AssistantResponse
    assistant.configuration = MagicMock()
    assistant.configuration.temperature = 0.5
    assistant.configuration.get = lambda k, d=None: getattr(
        assistant.configuration, k, d
    )  # Hack to support get() if we kept it, but we won't.
    assistant.model_provider = "gemini"  # Added required field
    assistant.linked_connectors = []
    assistant.instructions = "Be helpful."
    assistant.search_strategy = "hybrid"
    return assistant


@pytest.fixture
def mock_settings_service(mock_db):
    ss = MagicMock()
    ss.db = mock_db
    ss.get_value = AsyncMock()
    return ss


@pytest.fixture
def mock_vector_service(mock_settings_service):
    vs = MagicMock()
    vs.settings_service = mock_settings_service
    vs.get_embedding_model = AsyncMock()
    vs.get_async_qdrant_client = MagicMock()
    vs.get_collection_name = AsyncMock()
    vs.ensure_collection_exists = AsyncMock()  # Added mock
    return vs


@pytest.fixture
def chat_service(mock_db, mock_vector_service, mock_settings_service):
    # Removed db injection
    return ChatService(vector_service=mock_vector_service, settings_service=mock_settings_service)


# --- Tests ---


@pytest.mark.asyncio
async def test_stream_chat_nominal(chat_service, assistant_mock, mock_db):
    """Test nominal chat streaming using mocked components and split transactions."""

    # Mock Component Retrieval
    mock_components = {"llm": MagicMock(), "embed_model": MagicMock(), "search_strategy": MagicMock()}

    # Mock SessionLocal to return our mock_db
    # We use MagicMock for the context manager factory
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_db

    # Mock SettingsService constructor used inside _get_components
    with patch("app.services.chat_service.SettingsService") as mock_settings_cls:
        mock_scoped_settings = mock_settings_cls.return_value
        mock_scoped_settings.get_value = AsyncMock(
            side_effect=lambda k, default=None: "key" if "api_key" in k else "gemini-1.5-flash"
        )

        # Mock ChatRepository
        with (
            patch("app.services.chat_service.SessionLocal", side_effect=mock_session_cls),
            patch("app.services.chat_service.ChatRepository") as mock_repo_cls,
        ):

            mock_repo_instance = mock_repo_cls.return_value
            mock_repo_instance.add_message = AsyncMock()

            with patch.object(ChatService, "_get_components", return_value=mock_components) as mock_get_comps:
                # Mock RAGPipeline
                with patch("app.services.chat_service.RAGPipeline") as mock_pipeline_cls:
                    mock_pipeline_instance = mock_pipeline_cls.return_value

                    # Mock pipeline.run yielding events
                    async def mock_run_gen(message):
                        yield MagicMock(type="step", step_type="context", status="running")
                        yield MagicMock(type="step", step_type="context", status="completed", payload="Standalone?")

                        yield MagicMock(type="step", step_type="vectorization", status="running")
                        yield MagicMock(
                            type="step",
                            step_type="vectorization",
                            status="completed",
                            payload={"embedding": [0.1, 0.2]},
                        )  # Captured embedding

                        yield MagicMock(
                            type="sources", payload=[{"id": "n1", "text": "Source", "metadata": {}, "score": 0.9}]
                        )

                    # To differentiate logic between Retrieval pipeline and Synthesis pipeline runs:
                    async def mock_run_gen_retrieval(message):
                        yield MagicMock(type="step", step_type="context", status="completed", payload="Standalone?")
                        # Simulate side effect of populating ctx.retrieved_nodes if we could,
                        # but here we just test event flow.

                    async def mock_run_gen_synthesis(message):
                        async def token_gen():
                            yield MagicMock(delta="Hel")
                            yield MagicMock(delta="lo")

                        yield MagicMock(type="response_stream", payload=token_gen())

                    # We need side_effect for run to return different generators
                    # But RAGPipeline is instantiated twice.
                    # First instance is Retrieval, Second is Synthesis.
                    mock_pipeline_instance.run.side_effect = [
                        mock_run_gen_retrieval("Hi"),  # Retrieval
                        mock_run_gen_synthesis("Hi"),  # Synthesis
                    ]

                    # Mock broadcast/save tasks (background)
                    with patch.object(ChatService, "_safe_background_tasks", new_callable=AsyncMock):
                        # Execute
                        chunks = []
                        async for chunk in chat_service.stream_chat("Hi", assistant_mock, "session_1"):
                            chunks.append(json.loads(chunk))

                        # Verify
                        # 1. Check message saving (Start and End)
                        assert (
                            mock_repo_instance.add_message.call_count == 2
                        ), f"Expected 2 calls, got {mock_repo_instance.add_message.call_count}. Chunks: {chunks}"
                        mock_repo_instance.add_message.assert_has_calls(
                            [call("session_1", "user", "Hi"), call("session_1", "assistant", "Hello")]
                        )

                        # 2. Check SessionLocal usage
                        assert mock_session_cls.call_count >= 2


@pytest.mark.asyncio
async def test_get_components_success(
    chat_service, mock_settings_service, mock_vector_service, assistant_mock, mock_db
):
    """Test internal component retrieval logic."""

    # Mock Settings
    # Mock Settings
    # We strip the mocked 'get_value' on the injected mock_settings_service
    # and instead patch the SettingsService class because _get_components instantiates it.
    with patch("app.services.chat_service.SettingsService") as mock_settings_cls:
        mock_scoped_settings = mock_settings_cls.return_value

        async def get_val(key, default=None):
            if key == "gemini_api_key":
                return "key"
            if key == "gemini_chat_model":
                return "gemini-1.5-flash"
            return default

        mock_scoped_settings.get_value.side_effect = get_val

        # Mock LLM Factory
        with patch("app.services.chat_service.LLMFactory.create_llm", return_value="LLM_OBJ") as mock_create_llm:
            # Mock Vector Service
            mock_vector_service.get_embedding_model.return_value = "EMBED_OBJ"

            # Execute (Passing DB!)
            comps = await chat_service._get_components(assistant_mock, mock_db)

            assert comps["llm"] == "LLM_OBJ"
            assert comps["embed_model"] == "EMBED_OBJ"

            # Verify Factory call
            mock_create_llm.assert_called_with(
                provider="gemini", model_name="gemini-1.5-flash", api_key="key", temperature=0.5
            )


@pytest.mark.asyncio
async def test_stream_chat_config_error(chat_service, assistant_mock):
    """Test configuration error handling."""
    # Force error during component retrieval
    # Force error during component retrieval
    with (
        patch("app.services.chat_service.SessionLocal"),
        patch("app.services.chat_service.ChatRepository"),
        patch.object(ChatService, "_get_components", side_effect=ConfigurationError("No API Key")),
    ):
        chunks = []
        async for chunk in chat_service.stream_chat("Hi", assistant_mock, "session_1"):
            chunks.append(json.loads(chunk))

        # 0. Connection
        # 1. Error
        assert any(c.get("type") == "error" for c in chunks)


@pytest.mark.asyncio
async def test_reset_conversation(chat_service, mock_db):
    """Test reset conversation creates its own session."""

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_db

    with (
        patch("app.services.chat_service.SessionLocal", side_effect=mock_session_cls),
        patch("app.services.chat_service.ChatRepository") as mock_repo_cls,
    ):

        mock_repo_instance = mock_repo_cls.return_value
        mock_repo_instance.clear_history = AsyncMock()

        await chat_service.reset_conversation("session_1")

        mock_repo_instance.clear_history.assert_called_once_with("session_1")
        assert mock_session_cls.called
