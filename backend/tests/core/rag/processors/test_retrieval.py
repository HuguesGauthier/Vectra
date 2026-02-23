import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.rag.processors.retrieval import RetrievalProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from app.strategies.search.base import SearchResult, SearchMetadata


@pytest.fixture
def mock_ctx():
    assistant = MagicMock()
    assistant.top_k_retrieval = 5
    assistant.configuration = {"tags": ["acl1"]}
    assistant.retrieval_similarity_cutoff = 0.5

    search_strategy = AsyncMock()

    return PipelineContext(
        user_message="test query",
        chat_history=[],
        language="en",
        assistant=assistant,
        llm=None,
        embed_model=None,
        search_strategy=search_strategy,
    )


@pytest.mark.asyncio
async def test_retrieval_happy_path(mock_ctx):
    processor = RetrievalProcessor()

    # Mock search results
    results = [
        SearchResult(
            document_id="00000000-0000-0000-0000-000000000001",
            score=0.8,
            content="doc1",
            metadata=SearchMetadata(file_name="f1"),
        ),
        SearchResult(
            document_id="00000000-0000-0000-0000-000000000002",
            score=0.7,
            content="doc2",
            metadata=SearchMetadata(file_name="f2"),
        ),
    ]
    mock_ctx.search_strategy.search.return_value = results

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    assert len(mock_ctx.retrieved_nodes) == 2
    assert mock_ctx.retrieved_nodes[0].score == 0.8
    assert mock_ctx.retrieved_nodes[0].node.get_content() == "doc1"

    # Check events
    assert events[0].type == "step"
    assert events[0].status == "running"
    assert events[-1].type == "step"
    assert events[-1].status == "completed"
    assert "Retrieved 2" in events[-1].label


@pytest.mark.asyncio
async def test_retrieval_cutoff_filtering(mock_ctx):
    processor = RetrievalProcessor()

    # Mock search results: one above, one below 0.5
    results = [
        SearchResult(document_id="00000000-0000-0000-0000-000000000001", score=0.8, content="above"),
        SearchResult(document_id="00000000-0000-0000-0000-000000000002", score=0.3, content="below"),
    ]
    mock_ctx.search_strategy.search.return_value = results

    async for _ in processor.process(mock_ctx):
        pass

    assert len(mock_ctx.retrieved_nodes) == 1
    assert mock_ctx.retrieved_nodes[0].node.get_content() == "above"


@pytest.mark.asyncio
async def test_retrieval_error_handling(mock_ctx):
    processor = RetrievalProcessor()
    mock_ctx.search_strategy.search.side_effect = Exception("Search failed")

    events = []
    with pytest.raises(Exception):
        async for event in processor.process(mock_ctx):
            events.append(event)

    assert any(e.type == "step" and e.status == "failed" for e in events)


@pytest.mark.asyncio
async def test_retrieval_acl_extraction(mock_ctx):
    # Test string ACL conversion
    mock_ctx.assistant.configuration = {"tags": "single_tag"}
    processor = RetrievalProcessor()
    mock_ctx.search_strategy.search.return_value = []

    async for _ in processor.process(mock_ctx):
        pass

    # Verify SearchFilters were called with correct ACLs
    args, kwargs = mock_ctx.search_strategy.search.call_args
    filters = kwargs.get("filters")
    assert filters.user_acl == ["single_tag"]
