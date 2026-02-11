import pytest
from datetime import datetime, timezone
from app.schemas.dashboard_stats import ConnectStats, VectorizeStats, ChatStats, DashboardStats


def test_connect_stats_defaults():
    """Test default values in ConnectStats."""
    stats = ConnectStats()
    assert stats.active_pipelines == 0
    assert stats.total_connectors == 0
    assert stats.system_status == "ok"
    assert stats.last_sync_time is None


def test_connect_stats_validation():
    """Test ConnectStats validation constraints."""
    # Valid values
    stats = ConnectStats(
        active_pipelines=5, total_connectors=10, system_status="error", last_sync_time=datetime.now(timezone.utc)
    )
    assert stats.active_pipelines == 5
    assert stats.system_status == "error"

    # Negative values should fail
    with pytest.raises(ValueError):
        ConnectStats(active_pipelines=-1)


def test_vectorize_stats_defaults():
    """Test default values in VectorizeStats."""
    stats = VectorizeStats()
    assert stats.total_vectors == 0
    assert stats.total_tokens == 0
    assert stats.indexing_success_rate == 0.0
    assert stats.failed_docs_count == 0


def test_vectorize_stats_success_rate_range():
    """Test VectorizeStats success rate validation (0.0 - 1.0)."""
    # Valid range
    stats = VectorizeStats(indexing_success_rate=0.85)
    assert stats.indexing_success_rate == 0.85

    # Out of range should fail
    with pytest.raises(ValueError):
        VectorizeStats(indexing_success_rate=1.5)

    with pytest.raises(ValueError):
        VectorizeStats(indexing_success_rate=-0.1)


def test_vectorize_stats_negative_values():
    """Test VectorizeStats rejects negative values."""
    with pytest.raises(ValueError):
        VectorizeStats(total_vectors=-100)

    with pytest.raises(ValueError):
        VectorizeStats(failed_docs_count=-5)


def test_chat_stats_defaults():
    """Test default values in ChatStats."""
    stats = ChatStats()
    assert stats.monthly_sessions == 0
    assert stats.avg_latency_ttft == 0.0
    assert stats.total_tokens_used == 0


def test_chat_stats_validation():
    """Test ChatStats validation constraints."""
    stats = ChatStats(monthly_sessions=1000, avg_latency_ttft=0.25, total_tokens_used=50000)
    assert stats.monthly_sessions == 1000
    assert stats.avg_latency_ttft == 0.25

    # Negative latency should fail
    with pytest.raises(ValueError):
        ChatStats(avg_latency_ttft=-1.0)


def test_dashboard_stats_defaults():
    """Test DashboardStats creates nested structures with defaults."""
    stats = DashboardStats()

    # Check nested structures are created
    assert isinstance(stats.connect, ConnectStats)
    assert isinstance(stats.vectorize, VectorizeStats)
    assert isinstance(stats.chat, ChatStats)

    # Check defaults propagate
    assert stats.connect.active_pipelines == 0
    assert stats.vectorize.total_vectors == 0
    assert stats.chat.monthly_sessions == 0


def test_dashboard_stats_custom_values():
    """Test DashboardStats with custom nested values."""
    stats = DashboardStats(
        connect=ConnectStats(active_pipelines=3, total_connectors=10),
        vectorize=VectorizeStats(total_vectors=5000, indexing_success_rate=0.95),
        chat=ChatStats(monthly_sessions=500, avg_latency_ttft=0.3),
    )

    assert stats.connect.active_pipelines == 3
    assert stats.vectorize.indexing_success_rate == 0.95
    assert stats.chat.monthly_sessions == 500
