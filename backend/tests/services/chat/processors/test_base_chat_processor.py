import pytest
from app.services.chat.processors.base_chat_processor import BaseChatProcessor, ChatProcessorError
from app.services.chat.types import ChatContext

class TestBaseChatProcessor:
    def test_cannot_instantiate_abstract(self):
        """Should raise TypeError when instantiating abstract class."""
        with pytest.raises(TypeError):
            BaseChatProcessor()

    def test_concrete_implementation(self):
        """Should allow instantiation of concrete class implementing abstract methods."""
        
        class ConcreteProcessor(BaseChatProcessor):
            async def process(self, ctx: ChatContext):
                yield "test"

        processor = ConcreteProcessor()
        assert isinstance(processor, BaseChatProcessor)
        assert hasattr(processor, "logger")

    def test_error_structure(self):
        """Verify ChatProcessorError stores original error."""
        orig = ValueError("cause")
        err = ChatProcessorError("oops", original_error=orig)
        
        assert str(err) == "oops"
        assert err.original_error == orig
