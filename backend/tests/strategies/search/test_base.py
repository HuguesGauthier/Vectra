from unittest.mock import MagicMock, patch
import sys
import pytest
from uuid import uuid4
from pydantic import ValidationError

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.strategies.search.base import SearchFilters, SearchMetadata, SearchResult, SearchStrategy, SearchExecutionError


def test_search_filters_validation():
    """Happy Path: Valid filters."""
    f = SearchFilters(connector_id=uuid4(), status="INDEXED")
    assert f.status == "INDEXED"

    """Worst Case: Invalid status."""
    with pytest.raises(ValidationError):
        SearchFilters(status="BOOTING")

    """Worst Case: Unknown field (extra=forbid)."""
    with pytest.raises(ValidationError):
        SearchFilters(unknown_field="fail")


def test_search_metadata_truncation():
    """Happy Path: Large metadata is truncated."""
    large_val = "A" * 6000
    m = SearchMetadata(file_name="test.txt", custom_field=large_val)
    assert len(m.custom_field) <= 5015  # 5000 + "...[truncated]"
    assert m.custom_field.endswith("...[truncated]")


def test_search_result_validation():
    """Happy Path: Valid result."""
    res = SearchResult(
        document_id=uuid4(), score=0.95, content="Hello world", metadata=SearchMetadata(file_name="hello.txt")
    )
    assert res.score == 0.95

    """Worst Case: Invalid score."""
    with pytest.raises(ValidationError):
        SearchResult(document_id=uuid4(), score=1.5, content="fail")

    """Worst Case: Empty content."""
    with pytest.raises(ValidationError):
        SearchResult(document_id=uuid4(), score=0.5, content="")


@pytest.mark.asyncio
async def test_base_strategy_logging():
    """Happy Path: Verify logging boilerplate in base class."""

    class MockStrategy(SearchStrategy):
        @property
        def strategy_name(self) -> str:
            return "mock"

        async def search(self, query, top_k=10, filters=None):
            self._log_search_start(query, top_k)
            self._log_search_complete(1, 10.5)
            return []

    strategy = MockStrategy()
    with patch("app.strategies.search.base.logging.Logger.info") as mock_info:
        await strategy.search("test")
        assert mock_info.call_count == 2
        # Check first call extra data
        args, kwargs = mock_info.call_args_list[0]
        assert kwargs["extra"]["query_length"] == 4
        assert kwargs["extra"]["top_k"] == 10


from unittest.mock import patch
