"""
Unit tests for backend/app/models/chat_history.py

Tests cover:
- Happy path: Valid ChatHistory creation
- Edge cases: Optional fields
- Constraints: Verifying CheckConstraint exists
"""

from datetime import datetime
from uuid import UUID, uuid4

from app.models.chat_history import ChatHistory


class TestChatHistory:
    """Test suite for ChatHistory model."""

    # ========== HAPPY PATH ==========

    def test_create_valid_chat_history(self):
        """Test creating a valid ChatHistory instance."""
        session_id = "session-123"
        user_id = "user-456"
        assistant_id = uuid4()

        chat = ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content="Hello AI",
            assistant_id=assistant_id,
            metadata_={"tokens": 10},
        )

        assert chat.session_id == session_id
        assert chat.user_id == user_id
        assert chat.role == "user"
        assert chat.content == "Hello AI"
        assert chat.assistant_id == assistant_id
        assert chat.metadata_ == {"tokens": 10}
        assert isinstance(chat.id, UUID)

        # created_at is server_default, so it might be None on pure python init unless set
        # But we can set it manually for testing if needed, or check default is None
        assert chat.created_at is None

    def test_create_minimal_chat_history(self):
        """Test creating ChatHistory with only required fields."""
        session_id = "session-789"

        chat = ChatHistory(session_id=session_id, role="assistant", content="I am here.")

        assert chat.session_id == session_id
        assert chat.role == "assistant"
        assert chat.content == "I am here."
        assert chat.user_id is None
        assert chat.assistant_id is None
        assert chat.metadata_ is None

    # ========== DATA INTEGRITY ==========

    def test_role_constraint_exists(self):
        """Verify that the CheckConstraint for role is defined."""
        # Inspect the __table_args__ to find the CheckConstraint
        table_args = ChatHistory.__table_args__
        constraint_found = False

        for arg in table_args:
            if hasattr(arg, "name") and arg.name == "valid_role_check":
                constraint_found = True
                break

        assert constraint_found, "CheckConstraint 'valid_role_check' for role field is missing"

    def test_json_metadata_field(self):
        """Test metadata_ field accepts dictionary (JSON)."""
        data = {"source": "verified", "score": 0.95, "tags": ["ai", "chat"]}

        chat = ChatHistory(session_id="s1", role="system", content="System prompt", metadata_=data)

        assert chat.metadata_ == data
        assert chat.metadata_["score"] == 0.95

    # ========== EDGE CASES ==========

    def test_long_content(self):
        """Test creating ChatHistory with long content."""
        long_content = "A" * 5000
        chat = ChatHistory(session_id="s_long", role="user", content=long_content)
        assert chat.content == long_content

    def test_special_chars_in_content(self):
        """Test content with special characters."""
        content = "Hello 🌍! @#%^&*() \n New line."
        chat = ChatHistory(session_id="s_special", role="user", content=content)
        assert chat.content == content
