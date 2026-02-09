"""
Chat Schemas - Strictly typed requests and responses for Chat API.

ARCHITECT NOTE: Validated Payloads
These schemas enforce size limits to prevent DoS via payload stuffing.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Security Limits
MAX_MESSAGE_LENGTH = 50000  # Characters (prohibit massive copy-paste)
MAX_HISTORY_LENGTH = 100  # Messages
MAX_SESSION_ID_LENGTH = 100
MAX_CONTENT_LENGTH = 100000  # For history items (allow larger context but capped)


class MessageRole(str, Enum):
    """Allowed roles in chat history."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Single chat message."""

    role: MessageRole
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """
    Request payload for chat generation.
    """

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH, description="Current user query")
    assistant_id: UUID = Field(description="Target assistant UUID")
    session_id: str = Field(default="default", max_length=MAX_SESSION_ID_LENGTH, min_length=1)

    # Optional language hint for system prompt injection (e.g., "Respond in French")
    language: str = Field(default="en", max_length=10)

    # History injection (e.g. from client state or unrelated sessions)
    history: List[Message] = Field(default_factory=list, max_length=MAX_HISTORY_LENGTH)

    # Deep Chat Compatibility (Optional)
    messages: Optional[List[Dict[str, Any]]] = Field(default=None, description="Deep Chat format support")

    @model_validator(mode="before")
    @classmethod
    def parse_deep_chat_payload(cls, data: Any) -> Any:
        """
        Adapts Deep Chat's { messages: [{role, text}, ...] } payload
        to logical { message: str, history: List[Message] }.
        """
        if isinstance(data, dict) and "messages" in data and isinstance(data["messages"], list):
            raw_messages = data["messages"]
            if not raw_messages:
                return data

            # 1. Extract latest message as current query
            last_msg = raw_messages[-1]
            data["message"] = last_msg.get("text", "") or last_msg.get("content", "")

            # 2. Convert rest to history
            history_msgs = raw_messages[:-1]
            mapped_history = []

            for m in history_msgs:
                role = m.get("role", "user")
                content = m.get("text", "") or m.get("content", "")

                # Map Deep Chat 'ai' -> Backend 'assistant'
                if role == "ai":
                    role = "assistant"

                mapped_history.append({"role": role, "content": content})

            data["history"] = mapped_history

        return data


class SourceNode(BaseModel):
    """RAG Source Citation."""

    id: str
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None


class ChatResponse(BaseModel):
    """Chat completion response."""

    response: str
    sources: List[SourceNode] = Field(default_factory=list)
