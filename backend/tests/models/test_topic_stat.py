"""
Tests for TopicStat model.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.topic_stat import (MAX_CANONICAL_TEXT_LENGTH, MIN_FREQUENCY,
                                   TopicStat, TopicStatCreate, TopicStatUpdate)


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

    def test_default_frequency_is_one(self):
        """Default frequency should be 1."""
        topic = TopicStat(canonical_text="Test question", assistant_id=uuid4())
        assert topic.frequency == 1

    def test_empty_raw_variations(self):
        """raw_variations can be empty list."""
        topic = TopicStat(canonical_text="Test", assistant_id=uuid4(), raw_variations=[])
        assert topic.raw_variations == []

    def test_multiple_variations(self):
        """Multiple variations should be stored."""
        variations = ["reset my password", "forgot password", "password reset"]
        topic = TopicStat(canonical_text="Password reset", assistant_id=uuid4(), raw_variations=variations)
        assert len(topic.raw_variations) == 3


class TestTopicStatCreate:
    """Test TopicStatCreate schema."""

    def test_create_with_all_fields(self):
        """TopicStatCreate with all fields should work."""
        create = TopicStatCreate(
            canonical_text="What is AI?", frequency=10, raw_variations=["what's AI", "explain AI"], assistant_id=uuid4()
        )

        assert create.canonical_text == "What is AI?"
        assert create.frequency == 10
        assert len(create.raw_variations) == 2

    def test_create_defaults(self):
        """TopicStatCreate should have proper defaults."""
        create = TopicStatCreate(canonical_text="Test", assistant_id=uuid4())
        assert create.frequency == 1
        assert create.raw_variations == []

    def test_empty_canonical_text_fails(self):
        """Empty canonical text should fail."""
        with pytest.raises(ValidationError) as exc_info:
            TopicStatCreate(canonical_text="", assistant_id=uuid4())
        assert "canonical_text" in str(exc_info.value).lower()


class TestTopicStatUpdate:
    """Test TopicStatUpdate schema."""

    def test_update_frequency(self):
        """Update can modify frequency."""
        update = TopicStatUpdate(frequency=10)
        assert update.frequency == 10

    def test_update_variations(self):
        """Update can modify variations."""
        update = TopicStatUpdate(raw_variations=["new variation"])
        assert len(update.raw_variations) == 1
