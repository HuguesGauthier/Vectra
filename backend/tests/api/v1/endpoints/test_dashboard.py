import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.dashboard import (
    get_dashboard_stats,
    router,
    start_broadcast_task,
    stop_broadcast_task,
    broadcast_dashboard_stats_loop,
)
from app.schemas.dashboard_stats import (
    ChatStats,
    ConnectStats,
    DashboardStats,
    VectorizeStats,
)


@pytest.fixture
def app():
    from tests.utils import get_test_app

    app = get_test_app()
    app.include_router(router)
    return app


@pytest.fixture(autouse=True)
async def cleanup_background_tasks():
    import app.api.v1.endpoints.dashboard as dash_mod

    yield
    # Force stop background task
    dash_mod._broadcast_running = False
    if dash_mod._broadcast_task:
        dash_mod._broadcast_task.cancel()
        try:
            await dash_mod._broadcast_task
        except asyncio.CancelledError:
            pass
    dash_mod._broadcast_task = None


def test_get_dashboard_stats(app):
    mock_stats = DashboardStats(
        connect=ConnectStats(active_pipelines=1, total_connectors=2, system_status="ok", last_sync_time=None),
        vectorize=VectorizeStats(total_vectors=100, total_tokens=1000, indexing_success_rate=0.99, failed_docs_count=1),
        chat=ChatStats(monthly_sessions=50, avg_latency_ttft=0.5, total_tokens_used=5000),
    )

    with patch("app.api.v1.endpoints.dashboard.DashboardStatsService") as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_all_stats = AsyncMock(return_value=mock_stats)

        client = TestClient(app)
        response = client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["connect"]["active_pipelines"] == 1


def test_get_dashboard_stats_error(app):
    from app.core.exceptions import TechnicalError

    with patch("app.api.v1.endpoints.dashboard.DashboardStatsService") as MockService:
        mock_service_instance = MockService.return_value
        mock_service_instance.get_all_stats.side_effect = TechnicalError("Service Crash")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/stats")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "technical_error"


@pytest.mark.asyncio
async def test_broadcast_dashboard_stats_loop():
    import app.api.v1.endpoints.dashboard as dash_mod

    mock_db = AsyncMock()
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_manager = AsyncMock()
    mock_stats = DashboardStats(
        connect=ConnectStats(active_pipelines=1, total_connectors=2, system_status="ok", last_sync_time=None),
        vectorize=VectorizeStats(total_vectors=100, total_tokens=1000, indexing_success_rate=0.99, failed_docs_count=1),
        chat=ChatStats(monthly_sessions=50, avg_latency_ttft=0.5, total_tokens_used=5000),
    )

    async def stop_loop(*args, **kwargs):
        dash_mod._broadcast_running = False

    with (
        patch("app.core.database.SessionLocal", mock_session_local),
        patch("app.api.v1.endpoints.dashboard.DashboardStatsService") as MockService,
        patch("app.core.websocket.manager", mock_manager),
        patch("app.api.v1.endpoints.dashboard.asyncio.sleep", side_effect=stop_loop),
    ):

        MockService.return_value.get_all_stats = AsyncMock(return_value=mock_stats)
        await broadcast_dashboard_stats_loop(interval_seconds=1)

        assert MockService.return_value.get_all_stats.called
        assert mock_manager.emit_dashboard_stats.called


@pytest.mark.asyncio
async def test_broadcast_dashboard_stats_loop_exception():
    import app.api.v1.endpoints.dashboard as dash_mod

    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB Error"))
    mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

    async def stop_loop(*args, **kwargs):
        dash_mod._broadcast_running = False

    with (
        patch("app.core.database.SessionLocal", mock_session_local),
        patch("app.api.v1.endpoints.dashboard.asyncio.sleep", side_effect=stop_loop),
    ):

        await broadcast_dashboard_stats_loop(interval_seconds=1)
        assert mock_session_local.return_value.__aenter__.called


@pytest.mark.asyncio
async def test_start_stop_broadcast_task():
    import app.api.v1.endpoints.dashboard as dashboard_mod

    dashboard_mod._broadcast_task = None
    dashboard_mod._broadcast_running = False

    async def mock_loop(*args, **kwargs):
        while dashboard_mod._broadcast_running:
            await asyncio.sleep(0.01)

    with patch("app.api.v1.endpoints.dashboard.broadcast_dashboard_stats_loop", side_effect=mock_loop):
        await start_broadcast_task(interval_seconds=1)
        assert dashboard_mod._broadcast_task is not None
        assert dashboard_mod._broadcast_running is True
        await stop_broadcast_task()
        assert dashboard_mod._broadcast_task is None
        assert dashboard_mod._broadcast_running is False


@pytest.mark.asyncio
async def test_stop_broadcast_task_timeout():
    import app.api.v1.endpoints.dashboard as dashboard_mod

    mock_task = asyncio.Future()

    def cancel_side_effect():
        if not mock_task.done():
            mock_task.set_exception(asyncio.CancelledError())

    mock_task.cancel = MagicMock(side_effect=cancel_side_effect)
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
