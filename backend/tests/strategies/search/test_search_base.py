"""
Unit tests for hardened SearchStrategy base.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.strategies.search.base import (MAX_QUERY_LENGTH, MAX_TOP_K,
                                        SearchFilters, SearchMetadata,
                                        SearchResult, SearchStrategy)


class ConcreteSearchStrategy(SearchStrategy):
    """Concrete implementation for testing."""

    async def search(self, query: str, top_k: int = 10, filters=None):
        """Dummy implementation."""
        return []

    @property
    def strategy_name(self) -> str:
        return "TestStrategy"


class TestSearchResult:
    """Test SearchResult validation."""

    def test_valid_search_result(self):
        """✅ SUCCESS: Valid search result passes validation."""
        result = SearchResult(
            document_id=uuid4(), score=0.95, content="Test content", metadata=SearchMetadata(file_name="test.pdf")
        )

        assert isinstance(result.document_id, type(uuid4()))
        assert 0 <= result.score <= 1
        assert result.content == "Test content"

    def test_score_validation_fails_out_of_range(self):
        """❌ FAILURE: Score outside [0,1] range rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(document_id=uuid4(), score=1.5, content="Test", metadata=SearchMetadata())  # Invalid: > 1.0

        assert "score" in str(exc_info.value)

    def test_score_validation_fails_negative(self):
        """❌ FAILURE: Negative score rejected."""
        with pytest.raises(ValidationError):
            SearchResult(document_id=uuid4(), score=-0.1, content="Test", metadata=SearchMetadata())  # Invalid: < 0

    def test_content_truncation(self):
        """✅ SUCCESS: Huge content is limited."""
        huge_content = "x" * 200000  # 200KB

        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                document_id=uuid4(),
                score=0.8,
                content=huge_content,  # Should fail max_length
                metadata=SearchMetadata(),
            )

        assert "content" in str(exc_info.value)


class TestSearchFilters:
    """Test SearchFilters validation (P1 Security Fix)."""

    def test_valid_filters(self):
        """✅ SUCCESS: Valid filters accepted."""
        filters = SearchFilters(connector_id=uuid4(), status="INDEXED", user_acl=["user1", "user2"])

        assert filters.connector_id is not None
        assert filters.status == "INDEXED"

    def test_invalid_status_rejected(self):
        """❌ FAILURE: Invalid status rejected (prevents injection)."""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(status="INDEXED; DROP TABLE documents;--")  # SQL injection attempt

        assert "status" in str(exc_info.value)

    def test_extra_fields_rejected(self):
        """❌ FAILURE: Unknown fields rejected (prevents parameter pollution)."""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(connector_id=uuid4(), malicious_param="'; DROP TABLE users;--")

        assert "extra" in str(exc_info.value).lower()

    def test_acl_sanitization(self):
        """✅ SUCCESS: ACL entries are sanitized."""
        filters = SearchFilters(user_acl=["  user1  ", "", "   ", "user2"])

        # Should strip whitespace and remove empty
        assert "user1" in filters.user_acl
        assert "user2" in filters.user_acl
        assert len(filters.user_acl) == 2


class TestSearchStrategy:
    """Test SearchStrategy base class."""

    @pytest.mark.asyncio
    async def test_strategy_initialization(self):
        """✅ SUCCESS: Strategy initializes with logger."""
        strategy = ConcreteSearchStrategy()

        assert strategy.logger is not None
        assert strategy.strategy_name == "TestStrategy"

    @pytest.mark.asyncio
    async def test_logging_methods(self):
        """✅ SUCCESS: Logging methods work without errors."""
        strategy = ConcreteSearchStrategy()

        # Should not raise
        strategy._log_search_start("test query", 10)
        strategy._log_search_complete(5, 123.45)
        strategy._log_search_error(ValueError("test error"))


class TestSearchMetadata:
    """Test metadata validation."""

    def test_metadata_truncation(self):
        """✅ SUCCESS: Large metadata values are truncated."""
        huge_value = "x" * 10000

        # Use an extra field for this test, as defined fields have strict max_lengths
        metadata = SearchMetadata(custom_field=huge_value)

        # Should be truncated to 5000 + suffix
        assert len(metadata.custom_field) <= 5020
        assert "[truncated]" in metadata.custom_field
