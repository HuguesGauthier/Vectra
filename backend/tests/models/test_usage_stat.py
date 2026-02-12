"""
Tests for UsageStat model.
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.models.usage_stat import UsageStat


class TestUsageStatModel:
    """Test usage stat model."""

    def test_valid_usage_stat_creation(self):
        """Valid usage stat should be created."""
        assistant_id = uuid4()
        usage = UsageStat(
            assistant_id=assistant_id,
            session_id="sess_123",
            model="gpt-4",
            total_duration=1.5,
            input_tokens=100,
            output_tokens=50,
        )

        assert usage.total_duration == 1.5
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.assistant_id == assistant_id

    def test_default_values(self):
        """Default values should be set correctly."""
        usage = UsageStat(assistant_id=uuid4(), session_id="test", model="gpt-4")

        assert usage.total_duration == 0.0
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.user_id is None

    def test_with_user_id(self):
        """Usage stat with user_id should work."""
        user_id = uuid4()
        usage = UsageStat(assistant_id=uuid4(), session_id="test", model="gpt-4", user_id=user_id)
        assert usage.user_id == user_id

    def test_with_ttft(self):
        """Usage stat with TTFT should work."""
        usage = UsageStat(assistant_id=uuid4(), session_id="test", model="gpt-4", ttft=0.5)
        assert usage.ttft == 0.5

    def test_with_breakdown(self):
        """Usage stat with breakdown should work."""
        breakdown = {"retrieval": 0.3, "generation": 0.8}
        usage = UsageStat(assistant_id=uuid4(), session_id="test", model="gpt-4", step_duration_breakdown=breakdown)
        assert usage.step_duration_breakdown == breakdown

    def test_validation_on_assignment(self):
        """Validation should trigger on attribute assignment (Robustness P1)."""
        usage = UsageStat(assistant_id=uuid4(), session_id="test", model="gpt-4", total_duration=1.0)

        # Should raise ValidationError due to ge=0.0 constraint
        with pytest.raises(ValidationError):
            usage.total_duration = -1.0
