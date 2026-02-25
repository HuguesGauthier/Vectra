"""
Tests for TopicStat model.
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.models.topic_stat import TopicStat


class TestTopicStatModel:
    """Test topic stat model."""

    def test_valid_topic_stat_creation(self):
        """Valid topic stat should be created."""
        assistant_id = uuid4()

        topic = TopicStat(
            canonical_text="How do I reset my password?",
            frequency=5,
            raw_variations=["reset password", "forgot password"],
            assistant_id=assistant_id,
        )

        assert topic.canonical_text == "How do I reset my password?"
        assert topic.frequency == 5
        assert len(topic.raw_variations) == 2
        assert topic.assistant_id == assistant_id

    def test_default_frequency_is_one(self):
        """Default frequency should be 1."""
        topic = TopicStat(canonical_text="Test question", assistant_id=uuid4())
        assert topic.frequency == 1

    def test_validation_on_assignment(self):
        """Validation should trigger on attribute assignment (Robustness P1)."""
        topic = TopicStat(canonical_text="Test", assistant_id=uuid4(), frequency=1)

        # Should raise ValidationError due to ge=1 constraint
        with pytest.raises(ValidationError):
            topic.frequency = 0
