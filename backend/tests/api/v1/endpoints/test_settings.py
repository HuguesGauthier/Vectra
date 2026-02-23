import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.v1.endpoints.settings import get_settings_service, router
from app.core.security import get_current_user, get_current_admin
from app.models.user import User
from app.models.setting import Setting
from app.schemas.enums import UserRole
from app.models.enums import SettingGroup
from tests.utils import get_test_app

app = get_test_app()
app.include_router(router, prefix="/api/v1/settings")

# Mock Data
USER_ID = uuid4()
ADMIN_ID = uuid4()

mock_user = User(id=USER_ID, email="user@example.com", role=UserRole.USER, is_active=True)
mock_admin = User(id=ADMIN_ID, email="admin@example.com", role=UserRole.ADMIN, is_active=True)

mock_setting_public = Setting(key="app_language", value="fr", group=SettingGroup.GENERAL, is_secret=False)
mock_setting_secret = Setting(key="openai_api_key", value="sk-123", group=SettingGroup.AI, is_secret=True)


# Dependency Overrides
async def override_get_current_user():
    return mock_user


async def override_get_current_admin():
    return mock_admin


@pytest.fixture
def client():
    app.dependency_overrides = {}
    return TestClient(app)


def test_get_settings_masked(client):
    """Verify that secrets are masked in the GET response."""
    app.dependency_overrides[get_current_user] = override_get_current_user

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_all_settings.return_value = [mock_setting_public, mock_setting_secret]
    app.dependency_overrides[get_settings_service] = lambda: mock_service

    response = client.get("/api/v1/settings/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Check masking
    lang_setting = next(s for s in data if s["key"] == "app_language")
    assert lang_setting["value"] == "fr"

    key_setting = next(s for s in data if s["key"] == "openai_api_key")
    assert key_setting["value"] == "********"


def test_batch_update_settings(client):
    """Verify transactional batch update and result masking."""
    app.dependency_overrides[get_current_admin] = override_get_current_admin

    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    # Mocking the batch update return
    mock_service.update_settings_batch.return_value = [
        Setting(key="app_language", value="en", group=SettingGroup.GENERAL, is_secret=False),
        Setting(key="openai_api_key", value="sk-new", group=SettingGroup.AI, is_secret=True),
    ]
    app.dependency_overrides[get_settings_service] = lambda: mock_service

    payload = [{"key": "app_language", "value": "en"}, {"key": "openai_api_key", "value": "sk-new"}]

    response = client.put("/api/v1/settings/", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data[0]["value"] == "en"
    assert data[1]["value"] == "********"
    mock_service.update_settings_batch.assert_called_once()


def test_batch_update_unauthorized(client):
    """Verify non-admins are blocked from updating settings."""

    # We mock get_current_admin to fail
    async def fail_admin():
        from app.core.exceptions import FunctionalError

        raise FunctionalError("Forbidden", error_code="INSUFFICIENT_PRIVILEGES", status_code=403)

    app.dependency_overrides[get_current_admin] = fail_admin

    response = client.put("/api/v1/settings/", json=[{"key": "x", "value": "y"}])
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_batch_update_no_overwrite_with_placeholder(client):
    """Verify that internal service logic prevents overwriting with '********'."""
    # This is more of a service test, but we can verify coordination.
    # We'll use the real service with a mock repository to verify the value passed.

    from app.services.settings_service import SettingsService

    mock_repo = pytest.importorskip("unittest.mock").AsyncMock()
    mock_db = pytest.importorskip("unittest.mock").AsyncMock()

    # Existing secret setting
    existing = Setting(key="secret", value="real-value", is_secret=True)
    mock_repo.get_by_key.return_value = existing

    service = SettingsService(db=mock_db)
    service.repository = mock_repo

    # Attempt update with placeholder
    updates = [{"key": "secret", "value": "********", "is_secret": True}]
    result = await service.update_settings_batch(updates)

    # Verify DB was NOT notified of a change to 'value'
    # Actually our implementation just skips the update for that item
    assert result[0].value == "real-value"
    mock_db.add.assert_not_called()
