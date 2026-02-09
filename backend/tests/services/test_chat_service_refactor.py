from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.rag.types import PipelineEvent
from app.models.assistant import Assistant
from app.services.chat.types import ChatContext, PipelineStepType
from app.services.chat_service import ChatService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_deps():
    return {
        "vector_service": AsyncMock(),
        "settings_service": AsyncMock(),
        "chat_history_service": AsyncMock(),
        "cache_service": AsyncMock(),
    }


@pytest.fixture
def chat_service(mock_db, mock_deps):
    return ChatService(
        db=mock_db,
        vector_service=mock_deps["vector_service"],
        settings_service=mock_deps["settings_service"],
        chat_history_service=mock_deps["chat_history_service"],
        cache_service=mock_deps["cache_service"],
        trending_service_enabled=False,
    )


@pytest.mark.asyncio
async def test_pipeline_execution_flow(chat_service, mock_deps, capsys):
    """Test full RAG flow execution via Processors."""
    # Setup Mocks
    assistant = MagicMock(spec=Assistant)
    assistant.id = "asst_123"
    assistant.model_provider = "openai"
    assistant.model = "gpt-4"
    assistant.model = "gpt-4"
    assistant.use_semantic_cache = False
    assistant.search_strategy = "hybrid"
    assistant.configuration = {"temperature": 0.7}

    # Mock Settings to return string API Key
    mock_deps["settings_service"].get_value.return_value = "fake_api_key_123"

    # Mock Vectors to return BaseEmbedding spec
    from llama_index.core.embeddings import BaseEmbedding

    mock_embed = MagicMock(spec=BaseEmbedding)
    mock_deps["vector_service"].get_embedding_model.return_value = mock_embed

    # Mock LLMFactory to return generic match
    with patch("app.services.chat.processors.rag_processor.LLMFactory") as MockFactory:
        from llama_index.core.llms import LLM

        MockFactory.create_llm.return_value = MagicMock(spec=LLM)

    # Mock History
    mock_deps["chat_history_service"].get_history.return_value = []

    # Mock RAG Generation Processor internals
    # We patch the RAGGenerationProcessor._get_components or directly the dependencies used
    # But since _get_components is a method on the processor, we need to be careful.
    # Easiest is to mock internal calls of RAGGenerationProcessor.

    # But we are testing the Service orchestration.
    # Service instantiates processors.

    # To mock the RAG pipeline inside RAGGenerationProcessor, we can patch `app.services.chat_service.RAGPipeline`

    # To mock the RAG pipeline inside RAGGenerationProcessor, we can patch `app.services.chat.processors.rag_processor.RAGPipeline`

    with patch("app.services.chat.processors.rag_processor.RAGPipeline") as MockPipeline:
        pipeline_instance = MockPipeline.return_value

        async def event_generator(*args, **kwargs):
            # Async Generator helper
            async def async_gen(items):
                for i in items:
                    yield i

            from dataclasses import dataclass

            @dataclass
            class Chunk:
                delta: str

            yield PipelineEvent(type="step", step_type="retrieval", status="running", payload=None)
            yield PipelineEvent(type="step", step_type="retrieval", status="completed", payload={"count": 1})
            yield PipelineEvent(type="response_stream", payload=async_gen([Chunk(delta="Hello")]))

        pipeline_instance.run.side_effect = event_generator

        # ACT
        chunks = []
        async for chunk in chat_service.stream_chat(message="Hello", assistant=assistant, session_id="sess_123"):
            chunks.append(chunk)

        # ASSERT
        assert len(chunks) > 0
        with open("debug_results.log", "w") as f:
            from pprint import pformat

            f.write("CHUNKS:\n")
            f.write(pformat(chunks))
            f.write("\nCALLS:\n")
            f.write(pformat(mock_deps["chat_history_service"].add_message.call_args_list))

        # Verify History Loaded
        mock_deps["chat_history_service"].get_history.assert_awaited_once()
        # Verify Persistence (User + Assistant)
        assert mock_deps["chat_history_service"].add_message.call_count >= 2


@pytest.mark.asyncio
async def test_cache_hit_short_circuit(chat_service, mock_deps):
    """Test that Semantic Cache HIT stops execution before RAG."""
    assistant = MagicMock(spec=Assistant)
    assistant.id = "asst_123"
    assistant.use_semantic_cache = True

    # Mock Cache Service Hit
    mock_deps["cache_service"].get_cached_response.return_value = {
        "response": "Cached Answer",
        "sources": [{"text": "s1", "metadata": {"file_path": "f1"}}],
    }

    # Patch RAGPipeline to ensure it is NOT called
    with patch("app.services.chat.processors.rag_processor.RAGPipeline") as MockPipeline:
        chunks = []
        async for chunk in chat_service.stream_chat(message="Hello", assistant=assistant, session_id="sess_123"):
            chunks.append(chunk)

        # Assert RAG Pipeline was NOT instantiated
        MockPipeline.assert_not_called()

        # Assert Cache Response yielded
        assert any("Cached Answer" in c for c in chunks)

        # Assert Persistence still called (User + Assistant)
        # Note: In our design, UserPersistenceProcessor runs after CacheProcessor (if check passed)
        # Wait, if Cache HIT sets `should_stop=True`, subsequent processors check `if ctx.should_stop: return` or `break`.
        # In my implementation:
        # `UserPersistenceProcessor` does NOT check `should_stop`.
        # `RAGGenerationProcessor` DOES check `should_stop`.
        # `AssistantPersistenceProcessor` writes `ctx.full_response_text`.

        # So persistence should happen.
        assert mock_deps["chat_history_service"].add_message.call_count >= 2
