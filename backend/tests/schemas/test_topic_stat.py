"""
Unit tests for TopicStat schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.topic_stat import TopicStatCreate, TopicStatUpdate


class TestTopicStatCreate:
    """Test TopicStatCreate schema."""

    def test_create_with_all_fields(self):
        """TopicStatCreate with all fields should work."""
        assistant_id = uuid4()
        create = TopicStatCreate(
            canonical_text="What is AI?",
            frequency=10,
            raw_variations=["what's AI", "explain AI"],
            assistant_id=assistant_id,
        )

        assert create.canonical_text == "What is AI?"
        assert create.frequency == 10
        assert create.assistant_id == assistant_id
        assert len(create.raw_variations) == 2

    def test_create_defaults(self):
        """TopicStatCreate should have proper defaults."""
        create = TopicStatCreate(canonical_text="Test", assistant_id=uuid4())
        assert create.frequency == 1
        assert create.raw_variations == []

    def test_empty_canonical_text_fails(self):
        """Empty canonical text should fail."""
        with pytest.raises(ValidationError):
            TopicStatCreate(canonical_text="", assistant_id=uuid4())


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
