import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.chat.processors.history_processor import HistoryLoaderProcessor, TIMEOUT_HISTORY_LOAD
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.schemas.chat import Message


class TestHistoryLoaderProcessor:

    @pytest.fixture
    def mock_context(self):
        ctx = MagicMock(spec=ChatContext)
        ctx.metadata = {}
        ctx.session_id = "test-session"
        ctx.language = "en"
        ctx.chat_history_service = AsyncMock()
        ctx.metrics = MagicMock()
        ctx.history = []
        return ctx

    @pytest.mark.asyncio
    async def test_process_success(self, mock_context):
        """Should load history successfully and record metrics."""
        processor = HistoryLoaderProcessor()

        # Setup history data
        messages = [Message(role="user", content="Hello"), Message(role="assistant", content="Hi")]
        mock_context.chat_history_service.get_history.return_value = messages

        # Run processor
        events = []
        async for event in processor.process(mock_context):
            events.append(event)

        # Verify Context Update
        assert mock_context.history == messages

        # Verify Metrics
        mock_context.metrics.record_completed_step.assert_called_once()
        args = mock_context.metrics.record_completed_step.call_args[1]
        assert args["step_type"] == PipelineStepType.HISTORY_LOADING
        assert args["label"] == "History Loading"

        # Verify Events
        assert len(events) == 2  # Start + Complete

    @pytest.mark.asyncio
    async def test_process_timeout(self, mock_context):
        """Should fallback to empty history on timeout."""
        processor = HistoryLoaderProcessor()

        # Simulate slow history load
        async def slow_load(*args):
            await asyncio.sleep(TIMEOUT_HISTORY_LOAD + 0.1)
            return []

        # We patch the internal method or the service call.
        # Patching the service call is cleaner but wait_for wraps it.
        # Actually, asyncio.wait_for will cancel the task if it times out.
        # To test the timeout logic in the processor, we need the service to be slow.
        mock_context.chat_history_service.get_history.side_effect = slow_load

        # Run processor
        events = []
        async for event in processor.process(mock_context):
            events.append(event)

        # Verify Fallback
        assert mock_context.history == []

        # Verify Completion Event (Even on failure, we yield completion to unblock UI)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_process_error(self, mock_context):
        """Should fail open (empty history) on generic error."""
        processor = HistoryLoaderProcessor()

        # Simulate Error
        mock_context.chat_history_service.get_history.side_effect = ValueError("Redis Down")

        events = []
        async for event in processor.process(mock_context):
            events.append(event)

        # Verify Fallback
        assert mock_context.history == []

        # Verify Error Log (Implicit via logger mock if we checked, but context state is enough here)

    @pytest.mark.asyncio
    async def test_skip_no_session(self, mock_context):
        """Should skip processing if no session_id."""
        processor = HistoryLoaderProcessor()
        mock_context.session_id = None

        events = []
        async for event in processor.process(mock_context):
            events.append(event)

        assert len(events) == 0
        mock_context.chat_history_service.get_history.assert_not_called()
