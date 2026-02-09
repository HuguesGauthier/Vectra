"""
Tests for BaseRepository.
"""

import pytest

from app.repositories.base_repository import DEFAULT_LIMIT, MAX_LIMIT


class TestBaseRepositoryConstants:
    """Test repository constants."""

    def test_default_limit(self):
        """DEFAULT_LIMIT should be reasonable."""
        assert DEFAULT_LIMIT == 100
        assert isinstance(DEFAULT_LIMIT, int)

    def test_max_limit(self):
        """MAX_LIMIT should prevent DoS."""
        assert MAX_LIMIT == 1000
        assert MAX_LIMIT > DEFAULT_LIMIT

    def test_max_limit_is_reasonable(self):
        """MAX_LIMIT should not be too high."""
        assert MAX_LIMIT <= 10000  # Sanity check
