import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.rag.processors.vectorization import VectorizationProcessor
from app.core.rag.types import PipelineContext, PipelineEvent


@pytest.fixture
def mock_ctx():
    return PipelineContext(
        user_message="test query",
        chat_history=[],
        language="en",
        assistant=MagicMock(),
        llm=None,
        embed_model=AsyncMock(),
        search_strategy=None,
    )


@pytest.mark.asyncio
async def test_vectorization_happy_path(mock_ctx):
    processor = VectorizationProcessor()

    # Mock embedding
    mock_embedding = [0.1, 0.2, 0.3]
    mock_ctx.embed_model.aget_query_embedding.return_value = mock_embedding

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    assert mock_ctx.query_bundle.embedding == mock_embedding
    assert events[0].type == "step"
    assert events[0].status == "running"
    assert events[1].type == "step"
    assert events[1].status == "completed"
    assert events[1].payload["embedding"] == mock_embedding


@pytest.mark.asyncio
async def test_vectorization_uses_rewritten_query(mock_ctx):
    mock_ctx.rewritten_query = "rewritten query"
    processor = VectorizationProcessor()

    async for _ in processor.process(mock_ctx):
        pass

    mock_ctx.embed_model.aget_query_embedding.assert_called_with("rewritten query")


@pytest.mark.asyncio
async def test_vectorization_error_handling(mock_ctx):
    processor = VectorizationProcessor()
    mock_ctx.embed_model.aget_query_embedding.side_effect = Exception("Embedding Error")

    with pytest.raises(Exception):
        async for _ in processor.process(mock_ctx):
            pass
