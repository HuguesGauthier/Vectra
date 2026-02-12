import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat.processors.agentic_processor import AgenticProcessor
from app.services.chat.types import ChatContext


class TestAgenticProcessor:
    @pytest.fixture
    def mock_context(self):
        # Use a real ChatContext object to ensure proper behavior of attributes
        # and to avoid MagicMock/AsyncMock confusion in async iterators.
        from app.models.assistant import Assistant

        ctx = ChatContext(
            session_id="test_session",
            message="Hello",
            original_message="Hello",
            assistant=MagicMock(spec=Assistant),
            language="en",
            db=MagicMock(),
            settings_service=MagicMock(),
            vector_service=MagicMock(),
            chat_history_service=MagicMock(),
            cache_service=None,
        )
        ctx.metrics = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_should_skip(self, mock_context):
        processor = AgenticProcessor()

        mock_context.should_stop = True
        assert processor._should_skip(mock_context) is True

        mock_context.should_stop = False
        mock_context.query_engine_factory = None
        assert processor._should_skip(mock_context) is True

    @pytest.mark.asyncio
    async def test_contextualize_query_no_history(self, mock_context):
        import importlib
        import app.services.chat.processors.agentic_processor as mod

        importlib.reload(mod)
        processor = mod.AgenticProcessor()
        mock_context.history = []

        events = []
        async for event in processor._contextualize_query(mock_context):
            events.append(event)

        assert len(events) == 0

    @patch("app.factories.chat_engine_factory.ChatEngineFactory")
    @pytest.mark.asyncio
    async def test_perform_rewrite_call(self, mock_factory, mock_context):
        processor = AgenticProcessor()

        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.apredict.return_value = "Rewritten Query"

        # Configure Factory
        mock_factory.create_from_assistant = AsyncMock(return_value=mock_llm)

        mock_context.history = [MagicMock(role="user", content="Hi")]

        result = await processor._perform_rewrite_call(mock_context)

        assert result == "Rewritten Query"
        mock_llm.apredict.assert_called_once()

    @patch("app.factories.chat_engine_factory.ChatEngineFactory")
    @pytest.mark.asyncio
    async def test_detect_visualization_intent(self, mock_factory, mock_context):
        processor = AgenticProcessor()

        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.acomplete.return_value = "true"  # Returns text response

        mock_factory.create_from_assistant = AsyncMock(return_value=mock_llm)

        result = await processor._detect_visualization_intent(mock_context)

        assert result is True

        # Test Negative
        mock_llm.acomplete.return_value = "false"
        result = await processor._detect_visualization_intent(mock_context)
        assert result is False
