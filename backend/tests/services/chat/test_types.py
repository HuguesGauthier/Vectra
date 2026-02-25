import sys
from unittest.mock import MagicMock

# Mock problematic dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

import pytest
from unittest.mock import MagicMock
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus


def test_pipeline_step_type_enum():
    assert PipelineStepType.RETRIEVAL == "retrieval"
    assert PipelineStepType.COMPLETED == "completed"
    assert isinstance(PipelineStepType.RETRIEVAL, str)


def test_step_status_enum():
    assert StepStatus.RUNNING == "running"
    assert StepStatus.FAILED == "failed"


def test_chat_context_instantiation():
    # Mock dependencies
    mock_assistant = MagicMock()
    mock_db = MagicMock()
    mock_settings = MagicMock()
    mock_vector = MagicMock()
    mock_history = MagicMock()

    ctx = ChatContext(
        session_id="session_123",
        message="Hello",
        original_message="Hello",
        assistant=mock_assistant,
        language="fr",
        db=mock_db,
        settings_service=mock_settings,
        vector_service=mock_vector,
        chat_history_service=mock_history,
        cache_service=None,
    )

    assert ctx.session_id == "session_123"
    assert ctx.message == "Hello"
    assert ctx.should_stop is False
    assert isinstance(ctx.start_time, float)
    assert ctx.history == []


def test_chat_context_metadata_and_timers():
    mock_assistant = MagicMock()
    ctx = ChatContext(
        session_id="s",
        message="m",
        original_message="m",
        assistant=mock_assistant,
        language="en",
        db=MagicMock(),
        settings_service=MagicMock(),
        vector_service=MagicMock(),
        chat_history_service=MagicMock(),
        cache_service=None,
    )

    ctx.metadata["decision"] = "csv"
    ctx.step_timers["retrieval"] = 123.45

    assert ctx.metadata["decision"] == "csv"
    assert ctx.step_timers["retrieval"] == 123.45
