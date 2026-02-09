import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from app.core.rag.processors.reranking import (TIMEOUT_SECONDS,
                                               RerankingProcessor)
from app.core.rag.types import PipelineContext, PipelineEvent


# Mock Data
def create_mock_nodes(count=3):
    return [NodeWithScore(node=TextNode(text=f"Content {i}"), score=0.5) for i in range(count)]


@pytest.mark.asyncio
async def test_reranking_success_reordering():
    """✅ Success Case: LLM returns valid JSON ranking."""
    # Setup
    processor = RerankingProcessor()
    nodes = create_mock_nodes(3)

    ctx = MagicMock(spec=PipelineContext)
    ctx.retrieved_nodes = nodes
    ctx.user_message = "test query"
    ctx.assistant.use_reranker = True
    ctx.assistant.top_n_rerank = 3

    # Mock LLM Response
    # LLM says: Node 2 is best, then Node 0. Node 1 is irrelevant.
    mock_response = MagicMock()
    mock_response.text = "```json\n[2, 0]\n```"
    ctx.llm.acomplete = AsyncMock(return_value=mock_response)

    # Execute
    events = []
    async for event in processor.process(ctx):
        events.append(event)

    # Assert
    assert len(ctx.retrieved_nodes) == 2
    assert ctx.retrieved_nodes[0].node.text == "Content 2"  # First
    assert ctx.retrieved_nodes[1].node.text == "Content 0"  # Second

    # Verify synthetic scores
    assert ctx.retrieved_nodes[0].score == 1.0
    assert ctx.retrieved_nodes[1].score == 0.95


@pytest.mark.asyncio
async def test_reranking_timeout_fallback():
    """❌ Failure Case: LLM hangs -> Timeout Fallback."""
    # Setup
    processor = RerankingProcessor()
    nodes = create_mock_nodes(3)

    ctx = MagicMock(spec=PipelineContext)
    ctx.retrieved_nodes = nodes
    ctx.user_message = "infinite query"
    ctx.assistant.use_reranker = True
    ctx.assistant.top_n_rerank = 3

    # Mock LLM Hang
    async def infinite_sleep(*args, **kwargs):
        await asyncio.sleep(TIMEOUT_SECONDS + 1)
        return MagicMock(text="[]")

    ctx.llm.acomplete = AsyncMock(side_effect=infinite_sleep)

    # Execute
    events = []
    async for event in processor.process(ctx):
        events.append(event)

    # Assert
    # Should fall back to original order (0, 1, 2)
    assert len(ctx.retrieved_nodes) == 3
    assert ctx.retrieved_nodes[0].node.text == "Content 0"

    # Verify Error Event was emitted (FAIL OPEN)
    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 0  # We log warning but don't emit Pipeline Error for Timeout, we handle it gracefully?
    # Wait, my code emits error on Exception, but TimeoutError is caught specifically to fallback WITHOUT emitting error?
    # Let's check code...
    # except asyncio.TimeoutError: logger.warning... ranked_indices = ...
    # It catches Timeout, logs warning, sets ranked_indices, and PROCEEDS safely.
    # So NO pipeline error is expected. Correct.
