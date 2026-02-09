from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.assistant import Assistant, AssistantConfiguration
from app.services.chat_service import ChatService
from app.services.settings_service import SettingsService
from app.services.vector_service import VectorService


@pytest.fixture
def mock_deps():
    return {
        "vector_service": AsyncMock(spec=VectorService),
        "settings_service": AsyncMock(spec=SettingsService),
        "cache_service": AsyncMock(),
    }


@pytest.mark.asyncio
async def test_stream_chat_cache_hit(mock_deps):
    """
    Verify stream_chat flow when cache is hit.
    Should yield 'cache_lookup' steps and then cached tokens/sources.
    """
    service = ChatService(
        vector_service=mock_deps["vector_service"],
        settings_service=mock_deps["settings_service"],
        cache_service=mock_deps["cache_service"],
        trending_service_enabled=False,
    )

    # Mock Assistant
    assistant = Assistant(
        id=MagicMock(),
        model_provider="openai",
        model="gpt-4",
        configuration=AssistantConfiguration(temperature=0.7),
        use_semantic_cache=True,
    )

    # Mock Cache HIT
    cached_data = {
        "response": "Cached Answer",
        "sources": [{"metadata": {"file_path": "doc.pdf"}, "text": "content", "id": "1"}],
    }
    mock_deps["cache_service"].get_cached_response.return_value = cached_data

    # Run
    steps = []
    async for chunk in service.stream_chat("Hello", assistant, "session_1"):
        steps.append(chunk)

    # Verify
    assert any("cache_lookup_running" in s for s in steps)
    assert any("cache_lookup_completed" in s for s in steps)
    assert any("Cached Answer" in s for s in steps)  # Token

    # Verify RAG was NOT called (no retrieval steps)
    assert not any("retrieval_running" in s for s in steps)


@pytest.mark.asyncio
async def test_stream_chat_rag_fallback(mock_deps):
    """
    Verify stream_chat falls back to RAG when cache misses.
    """
    service = ChatService(
        vector_service=mock_deps["vector_service"],
        settings_service=mock_deps["settings_service"],
        cache_service=mock_deps["cache_service"],
        trending_service_enabled=False,
    )

    assistant = Assistant(
        id=MagicMock(),
        model_provider="openai",
        model="gpt-4",
        configuration=AssistantConfiguration(temperature=0.7),
        use_semantic_cache=True,
    )

    # Mock Cache MISS
    mock_deps["cache_service"].get_cached_response.return_value = None

    # Mock Pipeline Context & Run
    # This is complex due to internal pipeline construction.
    # We will check that it proceeds past cache step.

    # We need to mock SessionLocal to prevent DB errors
    with patch("app.services.chat_service.SessionLocal", new_callable=MagicMock):
        # We also need to mock RAGPipeline to avoid actual execution
        with patch("app.services.chat_service.RAGPipeline") as MockPipeline:
            pipeline_instance = MockPipeline.return_value

            # pipeline.run returns an async generator
            async def mock_gen(*args, **kwargs):
                from app.core.rag.types import PipelineEvent

                yield PipelineEvent(type="step", step_type="retrieval", status="running")
                yield PipelineEvent(type="step", step_type="retrieval", status="completed", payload={"count": 1})

            pipeline_instance.run.side_effect = mock_gen

            steps = []
            async for chunk in service.stream_chat("Hello", assistant, "session_1"):
                steps.append(chunk)

            # Verify Cache Miss -> Connection -> Retrieval
            assert any("cache_lookup_completed" in s for s in steps)
            assert any("retrieval_running" in s for s in steps)
