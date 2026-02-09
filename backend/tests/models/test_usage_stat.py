"""
Tests for UsageStat model.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.usage_stat import (ALLOWED_FEEDBACK_SCORES, ALLOWED_SENTIMENTS,
                                   UsageStat, UsageStatCreate, UsageStatUpdate)


class TestUsageStatModel:
    """Test usage stat model."""

    def test_valid_usage_stat_creation(self):
        """Valid usage stat should be created."""
        usage = UsageStat(
            assistant_id=uuid4(),
            session_id="sess_123",
            model="gpt-4",
            total_duration=1.5,
            input_tokens=100,
            output_tokens=50,
        )

        assert usage.total_duration == 1.5
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

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


class TestUsageStatCreate:
    """Test UsageStatCreate schema."""

    def test_create_with_all_fields(self):
        """UsageStatCreate with all fields should work."""
        create = UsageStatCreate(
            assistant_id=uuid4(),
            session_id="sess_456",
            user_id=uuid4(),
            model="gpt-4",
            total_duration=2.0,
            ttft=0.3,
            input_tokens=200,
            output_tokens=150,
            feedback_score=1,
            sentiment="positive",
        )

        assert create.total_duration == 2.0
        assert create.feedback_score == 1

    def test_create_minimal(self):
        """UsageStatCreate with minimal fields should work."""
        create = UsageStatCreate(assistant_id=uuid4(), session_id="test", model="gpt-4")

        assert create.total_duration == 0.0
        assert create.input_tokens == 0


class TestUsageStatUpdate:
    """Test UsageStatUpdate schema."""

    def test_update_feedback(self):
        """Update can modify feedback."""
        update = UsageStatUpdate(feedback_score=-1, sentiment="negative")

        assert update.feedback_score == -1
        assert update.sentiment == "negative"
