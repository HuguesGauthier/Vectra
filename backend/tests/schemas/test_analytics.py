from datetime import datetime, timezone
from app.schemas.analytics import AnalyticsResponse


def test_analytics_response_defaults():
    """Test defaults of AnalyticsResponse."""
    model = AnalyticsResponse()
    assert model.total_docs == 0
    assert model.estimated_cost == 0.0
    assert model.generated_at.tzinfo == timezone.utc


def test_analytics_response_generated_at_recent():
    """Test that generated_at is correctly set and recent."""
    model = AnalyticsResponse()
    now = datetime.now(timezone.utc)
    diff = now - model.generated_at
    assert diff.total_seconds() < 2


def test_analytics_response_partial_init():
    """Test partial initialization."""
    model = AnalyticsResponse(total_docs=100)
    assert model.total_docs == 100
    assert model.total_vectors == 0
