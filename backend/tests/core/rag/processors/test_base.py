import pytest
from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent


def test_base_processor_abstract_enforcement():
    # Verify that BaseProcessor cannot be instantiated directly
    with pytest.raises(TypeError):
        BaseProcessor()


@pytest.mark.asyncio
async def test_concrete_processor_implementation():
    # Create a simple concrete implementation for testing
    class ConcreteProcessor(BaseProcessor):
        async def process(self, ctx: PipelineContext):
            yield PipelineEvent(type="test", status="completed")

    processor = ConcreteProcessor()
    ctx = PipelineContext(
        user_message="test",
        chat_history=[],
        language="en",
        assistant=None,
        llm=None,
        embed_model=None,
        search_strategy=None,
    )

    events = []
    async for event in processor.process(ctx):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == "test"
    assert events[0].status == "completed"
