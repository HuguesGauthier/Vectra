import pytest
from pydantic import ValidationError

from app.core.rag.types import PipelineContext, PipelineEvent


class TestPipelineContext:
    def test_instantiation(self):
        ctx = PipelineContext(
            user_message="hello",
            chat_history=[],
            language="en",
            assistant=None,
            llm=None,
            embed_model=None,
            search_strategy=None,
        )
        assert ctx.user_message == "hello"
        assert ctx.retrieved_nodes == []


class TestPipelineEvent:
    def test_valid_event(self):
        event = PipelineEvent(type="step", status="running")
        assert event.type == "step"
        assert event.status == "running"
        assert event.payload is None

    def test_serialization(self):
        event = PipelineEvent(type="error", payload="boom")
        data = event.model_dump()
        assert data["type"] == "error"
        assert data["payload"] == "boom"

    def test_arbitrary_payload(self):
        """Should allow non-JSON objects if configured."""

        class ComplexObj:
            pass

        obj = ComplexObj()
        event = PipelineEvent(type="test", payload=obj)
        assert event.payload is obj
