import asyncio
import logging
import time
from typing import Annotated, Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import TechnicalError
from app.core.settings import settings as env_settings
from app.core.utils.model_normalization import normalize_model_name
from app.models.setting import Setting
from app.repositories.setting_repository import SettingRepository

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Refactored SettingsService.
    Hardens architecture via pure instance-based DI and batched operations.
    Fixes P1: Hybrid class/instance architecture and N+1 seeding.
    """

    # Shared Class-level state for cache (Global across instances in the same process)
    _cache: Dict[str, str] = {}
    _cache_loaded: bool = False
    _cache_last_updated: Optional[float] = None
    _cache_lock = asyncio.Lock()

    # Cache TTL in seconds (0 = no expiration)
    CACHE_TTL = 300  # 5 minutes

    DEFAULTS = {
        "ai_temperature": "0.2",
        "ai_top_k": "5",
        "app_language": "fr",
        "gen_ai_provider": "gemini",
        "gemini_chat_model": "gemini-1.5-flash-latest",
        "openai_chat_model": "gpt-4-turbo",
        "ui_dark_mode": "auto",
        "embedding_provider": "gemini",
        "gemini_api_key": "",
        "gemini_embedding_model": "models/text-embedding-004",
        "gemini_transcription_model": "gemini-1.5-flash-latest",
        "gemini_extraction_model": "gemini-1.5-flash-latest",
        "openai_api_key": "",
        "openai_embedding_model": "text-embedding-3-small",
        "local_embedding_url": "http://localhost:11434",
        "local_embedding_model": "nomic-embed-text",
        "analytics_cost_per_1k_tokens": "0.0001",
        "analytics_minutes_saved_per_doc": "5.0",
    }

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.repository = SettingRepository(db) if db else None

    def _is_cache_expired(self) -> bool:
        if not self.__class__._cache_loaded or self.CACHE_TTL == 0:
            return not self.__class__._cache_loaded

        if self.__class__._cache_last_updated is None:
            return True

        elapsed = time.time() - self.__class__._cache_last_updated
        return elapsed > self.CACHE_TTL

    async def load_cache(self, force: bool = False) -> None:
        """
        Refresh the shared settings cache from the database.
        """
        # If no DB, we can't load cache, but we might have it from another instance/process?
        # Actually in async, we rely on the in-memory static dict.
        # If repository is missing, we just skip DB refresh and rely on what we have (or defaults).
        if self.repository is None:
            return

        if not force and self.__class__._cache_loaded and not self._is_cache_expired():
            return

        async with self.__class__._cache_lock:
            # Re-check after lock
            if not force and self.__class__._cache_loaded and not self._is_cache_expired():
                return

            try:
                settings_list = await self.repository.get_all(limit=1000)
                self.__class__._cache = {s.key: s.value for s in settings_list}
                self.__class__._cache_loaded = True
                self.__class__._cache_last_updated = time.time()
                logger.info(f"Settings cache refreshed ({len(settings_list)} keys)")
            except Exception as e:
                logger.error(f"Failed to refresh settings cache: {e}", exc_info=True)
                # Don't raise here to allow fallback to env/defaults in get_value

    async def get_value(self, key: str, default: Any = None) -> str:
        """
        Retrieves a setting value with a modern multi-layer fallback:
        Instance Cache -> DB Refresh -> Env Var -> Hardcoded Default
        """
        # 1. Ensure cache is fresh using the instance's DB session
        if self._is_cache_expired():
            await self.load_cache()

        # 2. Check Cache
        value = self.__class__._cache.get(key)

        # 3. Fallback to Environment Variable
        if value is None or value == "":
            value = self._get_env_fallback(key)

        # 4. Fallback to Hardcoded Default
        if value is None or value == "":
            value = str(default) if default is not None else self.DEFAULTS.get(key, "")

        # 5. Normalization (Model names etc.)
        return normalize_model_name(key, value)

    def _get_env_fallback(self, key: str) -> Optional[str]:
        """Maps settings keys to pydantic-settings env vars."""
        env_map = {
            "gemini_api_key": env_settings.GEMINI_API_KEY,
            "openai_api_key": env_settings.OPENAI_API_KEY,
            "embedding_provider": env_settings.EMBEDDING_PROVIDER,
            "gemini_transcription_model": env_settings.GEMINI_TRANSCRIPTION_MODEL,
        }
        return env_map.get(key)

    async def update_setting(self, key: str, value: str, group: str = "general", is_secret: bool = False) -> Setting:
        """
        Atomic update of a setting and its corresponding cache.
        """
        log_val = "********" if is_secret else value
        logger.info(f"Updating setting: {key}={log_val}")

        try:
            setting = await self.repository.get_by_key(key)

            if not setting:
                setting = await self.repository.create(
                    {"key": key, "value": value, "group": group, "is_secret": is_secret}
                )
            else:
                # Protection against overwriting with masked placeholder from UI
                if is_secret and value == "********":
                    return setting

                # Use key-specific update method
                setting = await self.repository.update_by_key(
                    key,
                    {
                        "value": value,
                        "group": group,
                        "is_secret": is_secret,
                    },
                )

            # Atomic cache update
            async with self.__class__._cache_lock:
                self.__class__._cache[key] = setting.value

            return setting

        except Exception as e:
            logger.error(f"Failed to update setting {key}: {e}", exc_info=True)
            raise TechnicalError(f"Database error updating setting: {e}")

    async def seed_defaults(self) -> None:
        """
        Seeds missing default settings using optimized batching.
        Fixes P1: N+1 Seeding pattern.
        """
        try:
            existing_keys = await self.repository.get_all_keys()

            to_seed = []
            for key, default_val in self.DEFAULTS.items():
                if key not in existing_keys:
                    group = "ai" if any(x in key for x in ["ai", "embedding", "api_key"]) else "general"
                    is_secret = "api_key" in key

                    to_seed.append(
                        {
                            "key": key,
                            "value": default_val,
                            "group": group,
                            "is_secret": is_secret,
                            "description": f"Default {key}",
                        }
                    )

            if to_seed:
                logger.info(f"Seeding {len(to_seed)} missing settings...")
                await self.repository.create_batch(to_seed)
                await self.db.commit()
                # Refresh cache after massive insert
                await self.load_cache(force=True)

        except Exception as e:
            logger.error(f"Failed to seed defaults: {e}", exc_info=True)
            raise TechnicalError(f"Critical error seeding application settings: {e}")

    async def get_all_settings(self) -> List[Setting]:
        """Proxy to repository for list display."""
        return await self.repository.get_all(limit=1000)


async def get_settings_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SettingsService:
    """Dependency Provider."""
    return SettingsService(db)
