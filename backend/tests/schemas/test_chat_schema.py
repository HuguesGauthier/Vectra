"""
Tests for Chat Schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.chat import (MAX_HISTORY_LENGTH, MAX_MESSAGE_LENGTH,
                              ChatRequest, Message, MessageRole)


def test_chat_request_validation_success():
    req = ChatRequest(message="Hello", assistant_id=uuid4(), history=[Message(role=MessageRole.USER, content="Hi")])
    assert req.message == "Hello"
    assert len(req.history) == 1


def test_chat_request_invalid_role():
    with pytest.raises(ValidationError) as exc:
        Message(role="invalid", content="hi")
    assert "Input should be 'user', 'assistant' or 'system'" in str(exc.value)


def test_chat_request_message_too_long():
    long_msg = "a" * (MAX_MESSAGE_LENGTH + 1)
    with pytest.raises(ValidationError) as exc:
        ChatRequest(message=long_msg, assistant_id=uuid4())
    assert "String should have at most" in str(exc.value)


def test_chat_request_history_too_long():
    history = [Message(role=MessageRole.USER, content="x") for _ in range(MAX_HISTORY_LENGTH + 1)]
    with pytest.raises(ValidationError) as exc:
        ChatRequest(message="hi", assistant_id=uuid4(), history=history)
    assert "List should have at most" in str(exc.value)


def test_chat_request_invalid_uuid():
    with pytest.raises(ValidationError) as exc:
        ChatRequest(message="hi", assistant_id="invalid-uuid")
    assert "Input should be a valid UUID" in str(exc.value)
