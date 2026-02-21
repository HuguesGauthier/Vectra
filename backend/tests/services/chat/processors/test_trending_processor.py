import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from uuid import uuid4
from app.services.chat.processors.trending_processor import TrendingProcessor, TIMEOUT_TRENDING_ANALYSIS
from app.services.chat.types import ChatContext


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=ChatContext)
    ctx.metadata = {}
    ctx.session_id = str(uuid4())
    ctx.message = "Hello world"
    ctx.language = "en"
    ctx.db = MagicMock()
    ctx.db.commit = AsyncMock()
    ctx.db.rollback = AsyncMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_value = AsyncMock(return_value=None)
    ctx.vector_service = MagicMock()
    ctx.assistant = MagicMock()
    ctx.assistant.id = str(uuid4())
    ctx.assistant.model = "gpt-4o"
    ctx.assistant.model_provider = "openai"
    ctx.assistant.linked_connectors = []

    # Defaults for eligibility
    ctx.trending_enabled = True
    ctx.question_embedding = [0.1, 0.2, 0.3]
    ctx.captured_source_embedding = None

    # Metrics for usage
    ctx.user_id = str(uuid4())
    ctx.start_time = 1000.0
    # Metrics for usage
    ctx.user_id = str(uuid4())
    ctx.start_time = 1000.0
    ctx.metrics = MagicMock()
    ctx.metrics.record_completed_step = MagicMock()
    # ChatMetricsManager.get is a custom method, so MagicMock.get works,
    # BUT we need to return values or defaults.
    # The production code uses ctx.metrics.get(key, default)
    # MagicMock.get return a new mock by default.

    # We need to simulate dict-like behavior for get
    def mock_get(key, default=None):
        return default

    ctx.metrics.get.side_effect = mock_get

    return ctx


@pytest.mark.asyncio
async def test_should_run_trending_true(mock_context):
    processor = TrendingProcessor()
    assert processor._should_run_trending(mock_context) is True


@pytest.mark.asyncio
async def test_should_run_trending_false_disabled(mock_context):
    processor = TrendingProcessor()
    mock_context.trending_enabled = False
    assert processor._should_run_trending(mock_context) is False


@pytest.mark.asyncio
async def test_should_run_trending_false_no_embedding(mock_context):
    processor = TrendingProcessor()
    mock_context.question_embedding = None
    mock_context.captured_source_embedding = None
    assert processor._should_run_trending(mock_context) is False


@pytest.mark.asyncio
async def test_execute_trending_safe_success(mock_context):
    processor = TrendingProcessor()

    with (
        patch("app.services.chat.processors.trending_processor.TrendingService") as MockService,
        patch("app.services.chat.processors.trending_processor.TopicRepository"),
    ):

        mock_svc = MockService.return_value
        mock_svc.process_user_question = AsyncMock()

        async for _ in processor._execute_trending_safe(mock_context):
            pass

        mock_svc.process_user_question.assert_awaited_once()

        # Verify Metrics Recorded
        mock_context.metrics.record_completed_step.assert_called()
        call_args = mock_context.metrics.record_completed_step.call_args[1]
        assert call_args["step_type"] == "trending"
        assert call_args["label"] == "Analytics"
        assert call_args["duration"] is not None


@pytest.mark.asyncio
async def test_execute_trending_safe_timeout(mock_context):
    processor = TrendingProcessor()

    with (
        patch("app.services.chat.processors.trending_processor.TrendingService") as MockService,
        patch("app.services.chat.processors.trending_processor.TopicRepository"),
    ):

        mock_svc = MockService.return_value

        # Simulate a task that takes longer than the timeout
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(TIMEOUT_TRENDING_ANALYSIS + 0.1)

        mock_svc.process_user_question = AsyncMock(side_effect=slow_process)

        # We need to mock wait_for to actually raise TimeoutError because
        # real time sleeping in tests is flaky and slow.
        # But here we want to verifying the processor HANDLES the timeout.
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            async for _ in processor._execute_trending_safe(mock_context):
                pass

        # Should not raise exception, just log and finish

        # Verify Metrics Recorded even on timeout
        mock_context.metrics.record_completed_step.assert_called()
        call_args = mock_context.metrics.record_completed_step.call_args[1]
        assert call_args["duration"] == TIMEOUT_TRENDING_ANALYSIS


@pytest.mark.asyncio
async def test_persist_usage_statistics_safe(mock_context):
    processor = TrendingProcessor()

    with (
        patch("app.services.chat.processors.trending_processor.UsageRepository"),
        patch("app.services.chat.processors.trending_processor.PricingService"),
    ):

        async def _commit():
            pass

        async def _rollback():
            pass

        mock_context.db.commit.side_effect = _commit
        mock_context.db.rollback.side_effect = _rollback
        # Ensure add is mocked
        mock_context.db.add = MagicMock()

        await processor._persist_usage_statistics_safe(mock_context)

        mock_context.db.add.assert_called_once()
        mock_context.db.commit.assert_awaited_once()
