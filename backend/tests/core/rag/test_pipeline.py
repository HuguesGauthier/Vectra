import pytest
import asyncio
from typing import AsyncGenerator
from app.core.rag.pipeline import RAGPipeline
from app.core.rag.types import PipelineContext, PipelineEvent


class MockProcessor:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        if self.should_fail:
            raise ValueError("Processor failure")
        yield PipelineEvent(type="step", step_type="test", status="completed")


@pytest.mark.asyncio
async def test_rag_pipeline_happy_path():
    # Setup
    proc1 = MockProcessor()
    proc2 = MockProcessor()
    pipeline = RAGPipeline(processors=[proc1, proc2])

    # Run
    events = []
    async for event in pipeline.run("  hello  "):
        events.append(event)

    # Assert
    assert pipeline.ctx.user_message == "hello"  # Verified stripping
    assert len(events) == 2
    assert all(e.type == "step" for e in events)


@pytest.mark.asyncio
async def test_rag_pipeline_error_handling():
    # Setup
    proc1 = MockProcessor()
    proc2 = MockProcessor(should_fail=True)
    pipeline = RAGPipeline(processors=[proc1, proc2])

    # Run
    events = []
    async for event in pipeline.run("test"):
        events.append(event)

    # Assert
    # We expect 1 success event then 1 error event
    assert len(events) == 2
    assert events[0].type == "step"
    assert events[1].type == "error"
    assert "Processor failure" in events[1].payload


@pytest.mark.asyncio
async def test_rag_pipeline_empty_message():
    pipeline = RAGPipeline(processors=[MockProcessor()])
    async for _ in pipeline.run(None):
        pass
    assert pipeline.ctx.user_message == ""
