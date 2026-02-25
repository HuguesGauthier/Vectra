import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.settings_service import SettingsService
from app.models.setting import Setting


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    # Reset class-level cache for each test to avoid interference
    SettingsService._cache = {}
    SettingsService._cache_loaded = False
    SettingsService._cache_last_updated = None
    return SettingsService(mock_db)


@pytest.mark.asyncio
async def test_get_value_from_cache(service, mock_db):
    # Setup
    SettingsService._cache = {"my_key": "cached_value"}
    SettingsService._cache_loaded = True
    SettingsService._cache_last_updated = time.time()

    # Execute
    val = await service.get_value("my_key")

    # Verify
    assert val == "cached_value"


@pytest.mark.asyncio
async def test_get_value_fallback_to_defaults(service, mock_db):
    # Setup
    SettingsService._cache = {}
    SettingsService._cache_loaded = True
    SettingsService._cache_last_updated = time.time()

    # Execute
    # "ai_temperature" is in DEFAULTS as "0.2"
    val = await service.get_value("ai_temperature")

    # Verify
    assert val == "0.2"


@pytest.mark.asyncio
async def test_load_cache_refreshes_properly(service, mock_db):
    # Setup
    mock_setting = MagicMock(spec=Setting)
    mock_setting.key = "db_key"
    mock_setting.value = "db_value"

    service.repository.get_all = AsyncMock(return_value=[mock_setting])

    # Execute
    await service.load_cache(force=True)

    # Verify
    assert SettingsService._cache["db_key"] == "db_value"
    assert SettingsService._cache_loaded is True


@pytest.mark.asyncio
async def test_update_setting_atomicity(service, mock_db):
    # Setup
    mock_setting = MagicMock(spec=Setting)
    mock_setting.key = "new_key"
    mock_setting.value = "new_value"

    service.repository.get_by_key = AsyncMock(return_value=None)
    service.repository.create = AsyncMock(return_value=mock_setting)

    # Execute
    await service.update_setting("new_key", "new_value")

    # Verify
    assert SettingsService._cache["new_key"] == "new_value"
    service.repository.create.assert_called_once()


@pytest.mark.asyncio
async def test_cache_expiration_logic(service, mock_db):
    # Setup
    SettingsService._cache = {"old": "val"}
    SettingsService._cache_loaded = True
    # Simulate expiration (TTL is 300)
    SettingsService._cache_last_updated = time.time() - 400

    mock_setting = MagicMock(spec=Setting)
    mock_setting.key = "new"
    mock_setting.value = "val"
    service.repository.get_all = AsyncMock(return_value=[mock_setting])

    # Execute
    await service.get_value("any")

    # Verify load_cache was triggered
    service.repository.get_all.assert_called()
    assert "old" not in SettingsService._cache
    assert "new" in SettingsService._cache
