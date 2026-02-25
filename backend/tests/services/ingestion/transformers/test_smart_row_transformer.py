import sys
from unittest.mock import MagicMock
import pytest

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.schemas.ingestion import IndexingStrategy
from app.services.ingestion.transformers.smart_row_transformer import SmartRowTransformer


@pytest.fixture
def strategy():
    return IndexingStrategy(
        renaming_map={"old_title": "title", "old_val": "value"},
        semantic_cols=["title"],
        filter_exact_cols=["category", "id"],
        filter_range_cols=["value"],
        start_year_col="start",
        end_year_col="end",
    )


@pytest.fixture
def transformer(strategy):
    return SmartRowTransformer(strategy)


def test_transform_success(transformer):
    """Happy Path: Standard transformation with all features."""
    record = {
        "title": "Brake Pad A1",
        "category": "Brakes",
        "id": "123",
        "value": "19.99",
        "start": "2010",
        "end": "2012",
        "extra": "keep me",
    }

    semantic_text, payload = transformer.transform(record, line_number=1)

    # Semantic text check
    assert "title: Brake Pad A1" in semantic_text

    # Payload checks
    assert payload["category"] == "Brakes"
    assert payload["id"] == 123  # Enforced to int
    assert payload["value"] == 19.99  # Enforced to float
    assert payload["extra"] == "keep me"  # Lossless preservation
    assert payload["years_covered"] == [2010, 2011, 2012]
    assert payload["year_start"] == 2010
    assert payload["year_end"] == 2012
    assert payload["_line_number"] == 1


def test_transform_invalid_year_range(transformer):
    """Worst Case: end year < start year should skip enrichment."""
    record = {"title": "Bad Range", "start": "2020", "end": "2010"}

    _, payload = transformer.transform(record, line_number=2)

    assert "years_covered" not in payload
    assert payload["start"] == "2020"  # Original preserved


def test_transform_fallback_semantic(transformer):
    """Test fallback when no semantic columns are defined."""
    empty_strategy = IndexingStrategy(renaming_map={})
    transformer = SmartRowTransformer(empty_strategy)

    record = {"col1": "val1", "col2": "val2"}
    semantic_text, _ = transformer.transform(record, line_number=1)

    assert "col1: val1" in semantic_text
    assert "col2: val2" in semantic_text


def test_enforce_type_edge_cases(transformer):
    """Test various edge cases for type enforcement."""
    assert transformer._enforce_type("100") == 100
    assert transformer._enforce_type("100.5") == 100.5
    assert transformer._enforce_type("not a number") == "not a number"
    assert transformer._enforce_type("") is None
    assert transformer._enforce_type(None) is None
    assert transformer._enforce_type(123) == 123
