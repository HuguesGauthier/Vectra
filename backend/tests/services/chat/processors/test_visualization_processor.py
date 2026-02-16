import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat.processors.visualization_processor import VisualizationProcessor
from app.services.chat.types import ChatContext, PipelineStepType


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=ChatContext)
    ctx.session_id = "test_session"
    ctx.message = "show me a graph"  # Default trigger
    ctx.language = "en"
    ctx.visualization = None
    ctx.full_response_text = "Here is some data"
    ctx.sql_results = [{"col": 1}]  # Potential data
    ctx.retrieved_sources = []
    ctx.metadata = {}
    ctx.metrics = MagicMock()
    return ctx


@pytest.mark.asyncio
async def test_process_happy_path_viz_triggered(mock_context):
    # Setup
    processor = VisualizationProcessor()
    processor.viz_service = MagicMock()
    processor.viz_service.extract_data_info = AsyncMock()
    processor.viz_service.classify_visualization_type = AsyncMock()
    processor.viz_service.format_visualization_data = AsyncMock()

    # Mock Data Extraction
    mock_data_info = MagicMock()
    mock_data_info.row_count = 5
    processor.viz_service.extract_data_info.return_value = mock_data_info

    # Mock Classification
    processor.viz_service.classify_visualization_type.return_value = ("bar", {"input": 10, "output": 20})

    # Mock Formatting
    processor.viz_service.format_visualization_data.return_value = {"chart": "data"}

    # Execute
    events = []
    async for event in processor.process(mock_context):
        events.append(event)

    # Assertions
    assert len(events) > 0
    # Last event should be payload or completion
    assert '{"type": "visualization"' in events[-1]

    # Verify Metrics Recorded
    mock_context.metrics.record_completed_step.assert_called_with(
        step_type=PipelineStepType.VISUALIZATION_ANALYSIS,
        label="Visualization Analysis",
        duration=pytest.approx(0, abs=1),
        input_tokens=10,
        output_tokens=20,
    )


@pytest.mark.asyncio
async def test_process_skipped_eligibility(mock_context):
    # Setup: No data provided
    mock_context.sql_results = None
    mock_context.retrieved_sources = None
    mock_context.full_response_text = ""

    processor = VisualizationProcessor()

    # Execute
    events = []
    async for event in processor.process(mock_context):
        events.append(event)

    # Assertions
    assert len(events) == 0  # Early exit, no yield
    # Verify Metrics NOT Recorded (guard clause)
    mock_context.metrics.record_completed_step.assert_not_called()


@pytest.mark.asyncio
async def test_process_skipped_ai_decision(mock_context):
    # Setup: Message has NO keywords
    mock_context.message = "hello world"

    processor = VisualizationProcessor()
    processor.viz_service = MagicMock()
    processor.viz_service.extract_data_info = AsyncMock()
    processor.viz_service.classify_visualization_type = AsyncMock()

    # Execute
    events = []
    async for event in processor.process(mock_context):
        events.append(event)

    # Verify completed with skipped status
    assert "skipped_no_request" in events[-1]

    # Verify Metrics Recorded for "skipped"
    mock_context.metrics.record_completed_step.assert_called_with(
        step_type=PipelineStepType.VISUALIZATION_ANALYSIS,
        label="Visualization Analysis",
        duration=pytest.approx(0, abs=1),
        input_tokens=0,
        output_tokens=0,
    )

    # Verify extract_data_info NOT called
    processor.viz_service.extract_data_info.assert_not_called()


@pytest.mark.asyncio
async def test_process_error_fail_open(mock_context):
    # Setup
    processor = VisualizationProcessor()
    processor.viz_service = MagicMock()

    async def _extract(*args, **kwargs):
        raise Exception("Service Error")

    processor.viz_service.extract_data_info.side_effect = _extract
    processor.viz_service.classify_visualization_type = AsyncMock()

    # Execute
    events = []
    async for event in processor.process(mock_context):
        events.append(event)

    # Assertions
    assert "failed" in events[-1]
    assert "Service Error" in events[-1]


@pytest.mark.asyncio
async def test_process_redundant_table(mock_context):
    # Setup
    processor = VisualizationProcessor()
    processor.viz_service = MagicMock()
    processor.viz_service.extract_data_info = AsyncMock()
    processor.viz_service.classify_visualization_type = AsyncMock()

    mock_data_info = MagicMock()
    mock_data_info.row_count = 5
    processor.viz_service.extract_data_info.return_value = mock_data_info

    # Classified as TABLE
    processor.viz_service.classify_visualization_type.return_value = ("table", {})

    # Metadata says we ALREADY have a table
    mock_context.metadata = {"content_blocks": [{"type": "table"}]}

    # Execute
    events = []
    async for event in processor.process(mock_context):
        events.append(event)

    # Assertions: Should NOT yield visualization payload
    for event in events:
        assert '{"type": "visualization"' not in event
