import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from app.schemas.advanced_analytics import TTFTPercentiles, AssistantCost, AdvancedAnalyticsResponse, ConnectorSyncRate


def test_ttft_percentiles_validation():
    """Test TTFTPercentiles schema."""
    data = {"p50": 0.5, "p95": 1.2, "p99": 2.5, "period_hours": 24}
    model = TTFTPercentiles(**data)
    assert model.p50 == 0.5
    assert model.period_hours == 24


def test_assistant_cost_uuid_validation():
    """Test UUID validation in AssistantCost."""
    assistant_id = uuid4()
    data = {
        "assistant_id": str(assistant_id),
        "assistant_name": "Test Assistant",
        "total_tokens": 1000,
        "input_tokens": 500,
        "output_tokens": 500,
        "estimated_cost_usd": 0.01,
    }
    model = AssistantCost(**data)
    assert isinstance(model.assistant_id, UUID)
    assert model.assistant_id == assistant_id


def test_connector_sync_rate_constraints():
    """Test percent constraints in ConnectorSyncRate."""
    valid_data = {
        "connector_id": uuid4(),
        "connector_name": "Test",
        "success_rate": 99.5,
        "total_syncs": 10,
        "successful_syncs": 9,
        "failed_syncs": 1,
    }
    assert ConnectorSyncRate(**valid_data).success_rate == 99.5

    with pytest.raises(ValueError):
        ConnectorSyncRate(**{**valid_data, "success_rate": 101.0})


def test_advanced_analytics_response_generated_at():
    """Test that generated_at is aware and UTC."""
    model = AdvancedAnalyticsResponse()
    assert model.generated_at.tzinfo is not None
    assert model.generated_at.tzinfo == timezone.utc
    # Ensure it's very recent
    diff = datetime.now(timezone.utc) - model.generated_at
    assert diff.total_seconds() < 5


def test_from_attributes_support():
    """Test that schemas can be initialized from objects."""

    class MockObj:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    data = {"p50": 0.1, "p95": 0.2, "p99": 0.3, "period_hours": 1}
    mock = MockObj(**data)
    model = TTFTPercentiles.model_validate(mock)
    assert model.p50 == 0.1
