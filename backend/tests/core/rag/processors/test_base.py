import pytest

from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext


class TestBaseProcessor:
    """Test BaseProcessor abstract class enforcement."""

    def test_cannot_instantiate_abstract_class(self):
        """Should raise TypeError if instantiated directly."""
        with pytest.raises(TypeError):
            BaseProcessor()

    def test_subclass_must_implement_process(self):
        """Subclass failing to implement process should check."""

        class InvalidProcessor(BaseProcessor):
            pass

        with pytest.raises(TypeError):
            InvalidProcessor()

    @pytest.mark.asyncio
    async def test_concrete_implementation(self):
        """Proper subclass should work."""

        class ValidProcessor(BaseProcessor):
            async def process(self, ctx):
                yield "done"

        processor = ValidProcessor()
        assert processor is not None

        # Verify interface
        res = []
        async for item in processor.process(None):
            res.append(item)
        assert res == ["done"]
