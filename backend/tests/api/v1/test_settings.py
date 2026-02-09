from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.settings import router as settings_router
from app.core.security import get_current_admin, get_current_user
from app.models.setting import Setting
from app.services.settings_service import SettingsService, get_settings_service
from app.core.exceptions import TechnicalError, VectraException

# Mock service instance
mock_settings_svc = AsyncMock(spec=SettingsService)

async def mock_global_exception_handler(request: Request, exc: Exception):
    status_code = 500
    message = str(exc)
    if isinstance(exc, VectraException):
        status_code = exc.status_code
        message = exc.message
    return JSONResponse(
        status_code=status_code,
        content={"detail": message}
    )

# Setup isolated app for testing settings specifically
@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(settings_router)
    test_app.add_exception_handler(Exception, mock_global_exception_handler)
    test_app.add_exception_handler(VectraException, mock_global_exception_handler)

    # Override Auth and DB dependencies
    test_app.dependency_overrides[get_current_admin] = lambda: MagicMock(id="admin", email="admin@test.com")
    test_app.dependency_overrides[get_current_user] = lambda: MagicMock(id="admin", email="admin@test.com")

    # Override SettingsService
    async def override_get_service():
        return mock_settings_svc

    test_app.dependency_overrides[get_settings_service] = override_get_service

    return test_app


@pytest.fixture
def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def reset_mocks():
    mock_settings_svc.reset_mock()
    mock_settings_svc.get_all_settings = AsyncMock()
    mock_settings_svc.update_setting = AsyncMock()
    mock_settings_svc.seed_defaults = AsyncMock()


@pytest.mark.asyncio
async def test_get_settings(client):
    """
    Test GET / endpoints.
    """
    mock_settings = [
        Setting(key="ui_dark_mode", value="auto", group="general", is_secret=False),
        Setting(key="openai_api_key", value="sk-secret", group="ai", is_secret=True),
    ]
    mock_settings_svc.get_all_settings.return_value = mock_settings

    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for s in data:
        if s["key"] == "openai_api_key":
            assert s["value"] == "********"
    mock_settings_svc.seed_defaults.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_settings_error(client):
    """
    Test GET / endpoint error handling.
    """
    mock_settings_svc.seed_defaults.side_effect = Exception("Database error")

    response = await client.get("/")

    assert response.status_code == 500
    assert "Failed to fetch settings" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_settings_batch(client):
    """
    Test PUT / endpoint for batch updates.
    """
    payload = [
        {"key": "ui_dark_mode", "value": "dark", "group": "general", "is_secret": False},
        {"key": "openai_api_key", "value": "sk-new-fake-key", "group": "ai", "is_secret": True},
    ]

    updated_1 = Setting(key="ui_dark_mode", value="dark", group="general", is_secret=False)
    updated_2 = Setting(key="openai_api_key", value="sk-new-fake-key", group="ai", is_secret=True)

    mock_settings_svc.update_setting.side_effect = [updated_1, updated_2]

    response = await client.put("/", json=payload)

    assert response.status_code == 200
    updated_data = response.json()
    assert len(updated_data) == 2
    assert mock_settings_svc.update_setting.await_count == 2


@pytest.mark.asyncio
async def test_update_settings_error(client):
    """
    Test PUT / endpoint error handling.
    """
    payload = [{"key": "ui_dark_mode", "value": "dark", "group": "general", "is_secret": False}]
    mock_settings_svc.update_setting.side_effect = Exception("Update failed")

    response = await client.put("/", json=payload)

    assert response.status_code == 500
    assert "Failed to update settings" in response.json()["detail"]


@pytest.mark.asyncio
async def test_masked_secret_does_not_overwrite(client):
    """
    Verify that if we send '********', the service would receive it.
    """
    payload = [{"key": "openai_api_key", "value": "********", "group": "ai", "is_secret": True}]
    mock_ret = Setting(key="openai_api_key", value="original_value", group="ai", is_secret=True)
    mock_settings_svc.update_setting.return_value = mock_ret

    response = await client.put("/", json=payload)
    assert response.status_code == 200
    mock_settings_svc.update_setting.assert_awaited_with(
        key="openai_api_key", value="********", group="ai", is_secret=True
    )
