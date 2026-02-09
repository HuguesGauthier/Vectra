from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.rag.pipeline import RAGPipeline
from app.core.rag.types import PipelineEvent


@pytest.fixture
def mock_pipeline_dependencies():
    return {
        "llm": MagicMock(),
        "embed_model": MagicMock(),
        "search_strategy": MagicMock(),
        "assistant": MagicMock(),
        "chat_history": [],
    }


@pytest.mark.asyncio
async def test_pipeline_initialization(mock_pipeline_dependencies):
    """Verify context and processors are initialized."""
    with (
        patch("app.core.rag.pipeline.QueryRewriterProcessor") as MockRewriter,
        patch("app.core.rag.pipeline.VectorizationProcessor") as MockVec,
        patch("app.core.rag.pipeline.RetrievalProcessor") as MockRet,
        patch("app.core.rag.pipeline.RerankingProcessor") as MockRerank,
        patch("app.core.rag.pipeline.SynthesisProcessor") as MockSynth,
    ):

        pipeline = RAGPipeline(**mock_pipeline_dependencies)

        assert pipeline.ctx is not None
        assert pipeline.ctx.llm == mock_pipeline_dependencies["llm"]
        assert len(pipeline.processors) == 5

        # Verify instantiation of processors
        MockRewriter.assert_called_once()
        MockSynth.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_execution_flow(mock_pipeline_dependencies):
    """Verify pipeline iterates through all processors."""

    # Create mock processors that yield events
    processor1 = MagicMock()
    processor1.process = MagicMock(return_value=_async_yielder([PipelineEvent(type="p1")]))

    processor2 = MagicMock()
    processor2.process = MagicMock(return_value=_async_yielder([PipelineEvent(type="p2")]))

    with (
        patch("app.core.rag.pipeline.QueryRewriterProcessor", return_value=processor1),
        patch("app.core.rag.pipeline.VectorizationProcessor", return_value=processor2),
        patch("app.core.rag.pipeline.RetrievalProcessor", return_value=MagicMock(process=lambda x: _async_yielder([]))),
        patch("app.core.rag.pipeline.RerankingProcessor", return_value=MagicMock(process=lambda x: _async_yielder([]))),
        patch("app.core.rag.pipeline.SynthesisProcessor", return_value=MagicMock(process=lambda x: _async_yielder([]))),
    ):

        pipeline = RAGPipeline(**mock_pipeline_dependencies)

        events = []
        async for event in pipeline.run("Hello"):
            events.append(event)

        assert len(events) == 2
        assert events[0].type == "p1"
        assert events[1].type == "p2"

        # Verify context updated
        assert pipeline.ctx.user_message == "Hello"


@pytest.mark.asyncio
async def test_pipeline_error_handling(mock_pipeline_dependencies):
    """Verify pipeline catches exceptions and yields error event."""

    # Processor that raises exception
    bad_processor = MagicMock()
    # Mocking async generator failure is tricky.
    # We need process() to return an async generator that raises on next() or yields then raises.
    # Easiest is to make process() ITSELF raise, or returned generator raise.
    # Since `async for` awaits the iterator, if `process()` returns normally but yielding raises:

    async def _failing_yielder():
        yield PipelineEvent(type="ok")
        raise ValueError("Explosion")

    bad_processor.process.return_value = _failing_yielder()

    with (
        patch("app.core.rag.pipeline.QueryRewriterProcessor", return_value=bad_processor),
        patch("app.core.rag.pipeline.VectorizationProcessor"),
        patch("app.core.rag.pipeline.RetrievalProcessor"),
        patch("app.core.rag.pipeline.RerankingProcessor"),
        patch("app.core.rag.pipeline.SynthesisProcessor"),
    ):

        pipeline = RAGPipeline(**mock_pipeline_dependencies)

        events = []
        async for event in pipeline.run("Hello"):
            events.append(event)

        assert len(events) == 2  # 1 ok, 1 error
        assert events[0].type == "ok"
        assert events[1].type == "error"
        assert events[1].status == "failed"
        assert "Explosion" in str(events[1].payload)


async def _async_yielder(items):
    for item in items:
        yield item
