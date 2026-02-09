from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from app.schemas.chat import Message
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_stream_chat_pipeline_flow():
    # Mock Assistant
    assistant = MagicMock()
    assistant.id = "test-assistant-id"
    assistant.model = "gemini-1.5-flash"
    assistant.configuration = {"temperature": 0.5}
    assistant.linked_connectors = []
    assistant.instructions = "You are helpful."

    # Preparing Mocks for Components
    mock_llm = AsyncMock()
    mock_embed_model = MagicMock()
    mock_embed_model.aget_query_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    mock_search_strategy = AsyncMock()

    # Mock Rewriter Response
    mock_rewrite_response = MagicMock()
    mock_rewrite_response.text = "Standalone Question?"
    mock_llm.acomplete.return_value = mock_rewrite_response

    # Mock Synthesis Response
    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = [MagicMock(delta="Hello"), MagicMock(delta=" World")]
    mock_llm.astream_complete.return_value = mock_stream

    # Mock Search Results
    node1 = TextNode(text="Context 1", metadata={"file_name": "doc1"})
    node2 = TextNode(text="Context 2", metadata={"file_name": "doc2"})
    # Strategy returns generic result objects usually, but let's assume it returns objects
    # that RetrievalProcessor can convert.
    # Actually RetrievalProcessor expects objects with .content, .metadata, .score
    # Let's verify what RetrievalProcessor expects:
    # for res in search_results: TextNode(text=res.content, metadata=res.metadata)...

    mock_res1 = MagicMock()
    mock_res1.content = "Context 1"
    mock_res1.metadata = {"file_name": "doc1"}
    mock_res1.score = 0.9

    mock_res2 = MagicMock()
    mock_res2.content = "Context 2"
    mock_res2.metadata = {"file_name": "doc2"}
    mock_res2.score = 0.8

    mock_search_strategy.search.return_value = [mock_res1, mock_res2]

    # Patch _get_components to return our mocks
    with patch("app.services.chat_service.ChatService._get_components", new_callable=AsyncMock) as mock_get_components:
        mock_get_components.return_value = {
            "llm": mock_llm,
            "embed_model": mock_embed_model,
            "search_strategy": mock_search_strategy,
        }

        # Run Service
        history = [Message(role="user", content="Previous"), Message(role="assistant", content="Reply")]

        # Instantiate service with mocks
        service = ChatService(db=AsyncMock(), vector_service=MagicMock(), settings_service=MagicMock())

        # Call instance method
        # Args: message, assistant, session_id, language, history, user_id
        generator = service.stream_chat(
            message="Follow up", assistant=assistant, session_id="session_123", language="en", history=history
        )

        results = []
        async for chunk in generator:
            results.append(chunk)

        # 1. Verify Rewrite (Context Step)
        assert mock_llm.acomplete.called
        args, _ = mock_llm.acomplete.call_args
        assert "Chat History" in args[0]
        assert "Follow up" in args[0]

        # 2. Verify Vectorization
        assert mock_embed_model.aget_query_embedding.called

        # 3. Verify Search Strategy called with Standalone Question
        assert mock_search_strategy.search.called
        # Check args/kwargs robustly
        args, kwargs = mock_search_strategy.search.call_args
        query_arg = kwargs.get("query") if "query" in kwargs else (args[0] if args else None)
        assert query_arg == "Standalone Question?"

        # 4. Verify Sources Emitted in stream
        sources_chunk = next((r for r in results if '"type": "sources"' in r), None)
        assert sources_chunk is not None
        assert "Context 1" in sources_chunk

        # 5. Verify Synthesis
        assert mock_llm.astream_complete.called
        synth_args, _ = mock_llm.astream_complete.call_args
        assert "Context 1" in synth_args[0]
        # Legacy behavior: uses original user message for synthesis prompt, not rewritten one.
        assert "Follow up" in synth_args[0]
