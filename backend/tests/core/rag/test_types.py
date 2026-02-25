import pytest
from pydantic import ValidationError
from app.core.rag.types import PipelineContext, PipelineEvent


def test_pipeline_context_instantiation():
    # Happy path for PipelineContext (Dataclass)
    ctx = PipelineContext(
        user_message="test message",
        chat_history=[],
        language="en",
        assistant=None,
        llm=None,
        embed_model=None,
        search_strategy=None,
    )

    assert ctx.user_message == "test message"
    assert ctx.tools == []
    assert ctx.metadata == {}
    assert ctx.retrieved_nodes == []
    assert ctx.rewritten_query is None


def test_pipeline_event_validation():
    # Happy path for PipelineEvent (BaseModel)
    event = PipelineEvent(type="step", step_type="context", status="running", label="Processing context")
    assert event.type == "step"
    assert event.status == "running"

    # Payload can be anything
    event_with_payload = PipelineEvent(type="data", payload={"count": 10})
    assert event_with_payload.payload == {"count": 10}


def test_pipeline_event_arbitrary_types():
    # Verify arbitrary_types_allowed works (needed for LLM streams etc)
    class ArbitraryType:
        pass

    obj = ArbitraryType()
    event = PipelineEvent(type="stream", payload=obj)
    assert event.payload == obj


def test_pipeline_event_missing_required_fields():
    # Verify type is required
    with pytest.raises(ValidationError):
        PipelineEvent(status="running")
