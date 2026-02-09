from unittest.mock import AsyncMock, MagicMock

import pytest
from llama_index.core.schema import NodeWithScore

from app.core.rag.processors.retrieval import RetrievalProcessor
from app.core.rag.types import PipelineContext


@pytest.fixture
def pipeline_context():
    return PipelineContext(
        user_message="test query",
        chat_history=[],
        language="en",
        assistant=MagicMock(),
        llm=MagicMock(),
        embed_model=MagicMock(),
        search_strategy=MagicMock(),
    )


@pytest.mark.asyncio
async def test_retrieval_success_flow(pipeline_context):
    """Verify search execution and node conversion."""
    processor = RetrievalProcessor()

    # Mock search result
    mock_res = MagicMock()
    mock_res.content = "doc text"
    mock_res.metadata = {"source": "f1"}
    mock_res.score = 0.95

    pipeline_context.search_strategy.search = AsyncMock(return_value=[mock_res])
    pipeline_context.assistant.top_k_retrieval = 5
    pipeline_context.rewritten_query = "rewritten"

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    # Verify Search Call
    pipeline_context.search_strategy.search.assert_awaited_with(
        query="rewritten", top_k=5, filters={}  # Empty for now as per code
    )

    # Verify Context Update
    assert len(pipeline_context.retrieved_nodes) == 1
    node = pipeline_context.retrieved_nodes[0]
    assert node.score == 0.95
    assert node.node.get_content() == "doc text"

    # Verify Events
    assert len(events) == 3  # Start, Complete, Sources
    assert events[0].status == "running"
    assert events[1].status == "completed"
    assert events[2].type == "sources"
    assert events[2].payload[0]["text"] == "doc text"


@pytest.mark.asyncio
async def test_retrieval_fallback_query(pipeline_context):
    """Should use user_message if no rewritten_query."""
    processor = RetrievalProcessor()
    pipeline_context.search_strategy.search = AsyncMock(return_value=[])
    pipeline_context.rewritten_query = None  # forced

    async for _ in processor.process(pipeline_context):
        pass

    call_args = pipeline_context.search_strategy.search.call_args
    assert call_args.kwargs["query"] == "test query"


@pytest.mark.asyncio
async def test_retrieval_propagates_error(pipeline_context):
    """Should raise exception without yielding error event (pipeline job)."""
    processor = RetrievalProcessor()
    pipeline_context.search_strategy.search = AsyncMock(side_effect=TimeoutError("DB Timeout"))

    events = []
    # Assert it raises
    with pytest.raises(TimeoutError, match="DB Timeout"):
        async for event in processor.process(pipeline_context):
            events.append(event)

    # Verify only initial event yielded
    assert len(events) == 1
    assert events[0].type == "step"
    assert events[0].step_type == "retrieval"
    assert events[0].status == "running"
    # Bubbles up to pipeline
