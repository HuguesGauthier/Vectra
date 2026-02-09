import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.dashboard import (
    get_dashboard_stats,
    router,
    start_broadcast_task,
    stop_broadcast_task,
)
from app.schemas.dashboard_stats import (
    ChatStats,
    ConnectStats,
    DashboardStats,
    VectorizeStats,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_get_dashboard_stats(app):
    mock_stats = DashboardStats(
        connect=ConnectStats(
            active_pipelines=1,
            total_connectors=2,
            system_status="ok",
            last_sync_time=None,
        ),
        vectorize=VectorizeStats(
            total_vectors=100,
            total_tokens=1000,
            indexing_success_rate=0.99,
            failed_docs_count=1,
        ),
        chat=ChatStats(
            monthly_sessions=50, avg_latency_ttft=0.5, total_tokens_used=5000
        ),
    )

    with patch(
        "app.api.v1.endpoints.dashboard.DashboardStatsService"
    ) as MockService:
        mock_service_instance = MockService.return_value
        mock_service_instance.get_all_stats = AsyncMock(return_value=mock_stats)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["connect"]["active_pipelines"] == 1
        mock_service_instance.get_all_stats.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_dashboard_stats_loop():
    from app.api.v1.endpoints.dashboard import broadcast_dashboard_stats_loop

    mock_stats = DashboardStats(
        connect=ConnectStats(
            active_pipelines=1,
            total_connectors=2,
            system_status="ok",
            last_sync_time=None,
        ),
        vectorize=VectorizeStats(
            total_vectors=100,
            total_tokens=1000,
            indexing_success_rate=0.99,
            failed_docs_count=1,
        ),
        chat=ChatStats(
            monthly_sessions=50, avg_latency_ttft=0.5, total_tokens_used=5000
        ),
    )

    mock_db = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_db

    mock_manager = AsyncMock()

    # Use a side effect to stop the loop after one iteration
    async def stop_loop(*args, **kwargs):
        import app.api.v1.endpoints.dashboard as dashboard_mod

        dashboard_mod._broadcast_running = False

    with patch(
        "app.core.database.SessionLocal", mock_session_local
    ), patch(
        "app.api.v1.endpoints.dashboard.DashboardStatsService"
    ) as MockService, patch(
        "app.core.connection_manager.manager", mock_manager
    ), patch(
        "app.api.v1.endpoints.dashboard.asyncio.sleep", side_effect=stop_loop
    ):

        mock_service_instance = MockService.return_value
        mock_service_instance.get_all_stats = AsyncMock(return_value=mock_stats)

        await broadcast_dashboard_stats_loop(interval_seconds=1)

        assert mock_service_instance.get_all_stats.called
        assert mock_manager.emit_dashboard_stats.called


@pytest.mark.asyncio
async def test_broadcast_dashboard_stats_loop_exception():
    from app.api.v1.endpoints.dashboard import broadcast_dashboard_stats_loop

    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.side_effect = Exception("DB Error")

    async def stop_loop(*args, **kwargs):
        import app.api.v1.endpoints.dashboard as dashboard_mod

        dashboard_mod._broadcast_running = False

    with patch(
        "app.core.database.SessionLocal", mock_session_local
    ), patch(
        "app.api.v1.endpoints.dashboard.asyncio.sleep", side_effect=stop_loop
    ):

        await broadcast_dashboard_stats_loop(interval_seconds=1)
        # Should have caught the exception and called sleep
        assert mock_session_local.return_value.__aenter__.called


@pytest.mark.asyncio
async def test_start_stop_broadcast_task():
    # Reset global states
    import app.api.v1.endpoints.dashboard as dashboard_mod

    dashboard_mod._broadcast_task = None
    dashboard_mod._broadcast_running = False

    with patch(
        "app.api.v1.endpoints.dashboard.broadcast_dashboard_stats_loop",
        new_callable=AsyncMock,
    ):
        await start_broadcast_task(interval_seconds=1)
        assert dashboard_mod._broadcast_task is not None
        assert dashboard_mod._broadcast_running is True

        # Test starting when already running
        task_before = dashboard_mod._broadcast_task
        await start_broadcast_task(interval_seconds=1)
        assert dashboard_mod._broadcast_task is task_before

        # Test stopping
        await stop_broadcast_task()
        assert dashboard_mod._broadcast_task is None
        assert dashboard_mod._broadcast_running is False


@pytest.mark.asyncio
async def test_stop_broadcast_task_timeout():
    import app.api.v1.endpoints.dashboard as dashboard_mod

    mock_task = MagicMock()
    dashboard_mod._broadcast_task = mock_task
    dashboard_mod._broadcast_running = True

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        await stop_broadcast_task()
        assert mock_task.cancel.called
        assert dashboard_mod._broadcast_task is None
        assert dashboard_mod._broadcast_running is False


@pytest.mark.asyncio
async def test_stop_broadcast_task_none():
    import app.api.v1.endpoints.dashboard as dashboard_mod

    dashboard_mod._broadcast_task = None
    await stop_broadcast_task()
    # Should just return without error
