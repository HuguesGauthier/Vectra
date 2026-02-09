"""
Tests for AssistantRepository.
"""

import pytest

from app.repositories.assistant_repository import (DEFAULT_LIMIT, MAX_LIMIT,
                                                   AssistantRepository)


class TestAssistantRepository:
    """Basic repository structure tests."""

    def test_initialization(self):
        """Repository constants should be defined correctly."""
        assert DEFAULT_LIMIT == 100
        assert MAX_LIMIT == 1000

    def test_limit_enforcement(self):
        """MAX_LIMIT should be greater than DEFAULT_LIMIT."""
        assert MAX_LIMIT > DEFAULT_LIMIT
