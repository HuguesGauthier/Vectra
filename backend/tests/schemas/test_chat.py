import pytest
from uuid import uuid4
from app.schemas.chat import (
    ChatRequest,
    Message,
    MessageRole,
    SourceNode,
    ChatResponse,
    MAX_MESSAGE_LENGTH,
    MAX_HISTORY_LENGTH,
)


def test_chat_request_basic():
    """Test basic ChatRequest creation."""
    request = ChatRequest(message="Hello", assistant_id=uuid4())
    assert request.message == "Hello"
    assert request.session_id == "default"
    assert request.language == "en"
    assert request.history == []


def test_chat_request_dos_protection_message_length():
    """Test DoS protection for message length."""
    with pytest.raises(ValueError):
        ChatRequest(message="x" * (MAX_MESSAGE_LENGTH + 1), assistant_id=uuid4())


def test_chat_request_dos_protection_history_length():
    """Test DoS protection for history length."""
    with pytest.raises(ValueError):
        ChatRequest(
            message="test",
            assistant_id=uuid4(),
            history=[Message(role=MessageRole.USER, content="msg") for _ in range(MAX_HISTORY_LENGTH + 1)],
        )


def test_deep_chat_payload_parsing():
    """Test Deep Chat format conversion."""
    deep_chat_payload = {
        "assistant_id": str(uuid4()),
        "messages": [
            {"role": "user", "text": "First message"},
            {"role": "ai", "text": "AI response"},
            {"role": "user", "text": "Latest message"},
        ],
    }

    request = ChatRequest(**deep_chat_payload)

    # Latest message should be extracted
    assert request.message == "Latest message"

    # History should contain previous messages as Message objects
    assert len(request.history) == 2
    assert request.history[0].content == "First message"
    assert request.history[1].role == MessageRole.ASSISTANT  # ai -> assistant mapping


def test_deep_chat_ai_role_mapping():
    """Test that 'ai' role is mapped to 'assistant'."""
    payload = {
        "assistant_id": str(uuid4()),
        "messages": [{"role": "ai", "text": "AI message"}, {"role": "user", "text": "User message"}],
    }

    request = ChatRequest(**payload)
    assert request.history[0].role == MessageRole.ASSISTANT


def test_message_validation():
    """Test Message validation."""
    msg = Message(role=MessageRole.USER, content="Test content")
    assert msg.role == MessageRole.USER
    assert msg.content == "Test content"

    # Empty content should fail
    with pytest.raises(ValueError):
        Message(role=MessageRole.USER, content="")


def test_source_node_uuid():
    """Test SourceNode with UUID."""
    node_id = uuid4()
    source = SourceNode(id=node_id, text="Sample text", metadata={"file": "test.pdf"}, score=0.95)
    assert source.id == node_id
    assert source.score == 0.95


def test_chat_response():
    """Test ChatResponse creation."""
    response = ChatResponse(response="Answer text", sources=[SourceNode(id=uuid4(), text="Source 1", metadata={})])
    assert response.response == "Answer text"
    assert len(response.sources) == 1
