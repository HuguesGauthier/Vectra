import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.setting import Setting
from app.services.settings_service import SettingsService


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def service(mock_db_session):
    # Reset class cache for tests
    SettingsService._cache = {}
    SettingsService._cache_loaded = False
    SettingsService._cache_last_updated = None

    s = SettingsService(mock_db_session)
    s.repository = AsyncMock()

    # AsyncMock automatically provides awaitable children, but we can be explicit
    s.repository.get_all.return_value = []
    s.repository.get_by_key.return_value = None
    s.repository.create.return_value = MagicMock(spec=Setting)
    s.repository.create_batch.return_value = None
    s.repository.get_all_keys.return_value = []

    return s


@pytest.mark.asyncio
async def test_get_value_cache_lookup(service):
    """Verify that get_value uses the cached value if loaded."""
    SettingsService._cache = {"test_key": "cached_value"}
    SettingsService._cache_loaded = True
    SettingsService._cache_last_updated = time.time()

    val = await service.get_value("test_key")
    assert val == "cached_value"
    # Ensure no DB call was made
    service.repository.get_all.assert_not_called()


@pytest.mark.asyncio
async def test_get_value_refresh_on_expire(service):
    """Verify that a refresh is triggered when cache is expired."""
    SettingsService._cache = {"old_key": "old_value"}
    SettingsService._cache_loaded = True
    SettingsService._cache_last_updated = time.time() - 1000  # Expired

    mock_setting = MagicMock(spec=Setting)
    mock_setting.key = "new_key"
    mock_setting.value = "new_value"

    service.repository.get_all.return_value = [mock_setting]

    val = await service.get_value("new_key")
    assert val == "new_value"
    service.repository.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_seed_defaults_batching(service, mock_db_session):
    """Verify that seed_defaults uses create_batch."""
    existing_keys = list(SettingsService.DEFAULTS.keys())
    if existing_keys:
        missing_key = existing_keys.pop()
    else:
        # Fallback if DEFAULTS is empty (unlikely but safe)
        SettingsService.DEFAULTS["test"] = "val"
        missing_key = "test"
        existing_keys = []

    service.repository.get_all_keys.return_value = existing_keys

    await service.seed_defaults()

    service.repository.create_batch.assert_called_once()
    assert len(service.repository.create_batch.call_args[0][0]) == 1
    assert service.repository.create_batch.call_args[0][0][0]["key"] == missing_key


@pytest.mark.asyncio
async def test_update_setting_cache_sync(service):
    """Verify that update_setting synchronizes the global cache."""
    mock_setting = MagicMock(spec=Setting)
    mock_setting.key = "updated_key"
    mock_setting.value = "updated_value"

    service.repository.get_by_key.return_value = None
    service.repository.create.return_value = mock_setting

    await service.update_setting("updated_key", "updated_value")

    assert SettingsService._cache["updated_key"] == "updated_value"
    service.repository.create.assert_called_once()


@pytest.mark.asyncio
async def test_normalization_integration(service):
    """Verify that normalization logic is applied to return values."""
    SettingsService._cache = {"gemini_chat_model": "flash-2.0"}
    SettingsService._cache_loaded = True
    SettingsService._cache_last_updated = time.time()

    val = await service.get_value("gemini_chat_model")
    assert val == "models/flash-2.0"
