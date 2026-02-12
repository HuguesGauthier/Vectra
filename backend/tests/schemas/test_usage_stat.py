"""
Unit tests for UsageStat schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.usage_stat import UsageStatCreate, UsageStatUpdate


class TestUsageStatCreate:
    """Test UsageStatCreate schema."""

    def test_create_with_all_fields(self):
        """UsageStatCreate with all fields should work."""
        assistant_id = uuid4()
        user_id = uuid4()
        create = UsageStatCreate(
            assistant_id=assistant_id,
            session_id="sess_456",
            user_id=user_id,
            model="gpt-4",
            total_duration=2.0,
            ttft=0.3,
            input_tokens=200,
            output_tokens=150,
        )

        assert create.total_duration == 2.0
        assert create.session_id == "sess_456"
        assert create.assistant_id == assistant_id
        assert create.user_id == user_id

    def test_create_minimal(self):
        """UsageStatCreate with minimal fields should work."""
        create = UsageStatCreate(assistant_id=uuid4(), session_id="test", model="gpt-4")

        assert create.total_duration == 0.0
        assert create.input_tokens == 0

    def test_empty_session_id_fails(self):
        """Empty session_id should fail."""
        with pytest.raises(ValidationError):
            UsageStatCreate(assistant_id=uuid4(), session_id="", model="gpt-4")


class TestUsageStatUpdate:
    """Test UsageStatUpdate schema."""

    def test_update_performance(self):
        """Update can modify duration and tokens."""
        update = UsageStatUpdate(total_duration=5.0, input_tokens=1000)
        assert update.total_duration == 5.0
        assert update.input_tokens == 1000

    def test_invalid_duration_rejected(self):
        """Negative duration should be rejected."""
        with pytest.raises(ValidationError):
            UsageStatUpdate(total_duration=-1.0)
