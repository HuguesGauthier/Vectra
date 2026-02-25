import asyncio
import logging
import time
from typing import Annotated, Any, Dict, List, Optional, Set

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
        "mistral_chat_model": "mistral-large-latest",
        "mistral_temperature": "0.7",
        "mistral_top_k": "50",
        "ollama_base_url": "",
        "ollama_chat_model": "mistral",
        "ollama_embedding_model": "bge-m3",
        "ollama_temperature": "0.7",
        "ollama_top_k": "40",
        "ui_dark_mode": "auto",
        "embedding_provider": "ollama",
        "gemini_api_key": "",
        "gemini_embedding_model": "models/text-embedding-004",
        "gemini_transcription_model": "gemini-1.5-flash-latest",
        "gemini_extraction_model": "gemini-1.5-flash-latest",
        "gemini_temperature": "0.7",
        "gemini_top_k": "40",
        "openai_api_key": "",
        "openai_embedding_model": "text-embedding-3-small",
        "openai_chat_model": "gpt-4-turbo",
        "openai_temperature": "0.7",
        "openai_top_k": "0",  # OpenAI doesn't use top_k, but keep for consistency
        "local_embedding_model": "nomic-embed-text",
        "local_extraction_model": "mistral",
        "local_extraction_url": "",
        "analytics_cost_per_1k_tokens": "0.0001",
        "analytics_minutes_saved_per_doc": "5.0",
        "rerank_provider": "cohere",
        "local_rerank_model": "BAAI/bge-reranker-base",
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
        if value is None:
            value = self._get_env_fallback(key)

        # 4. Fallback to Hardcoded Default
        if value is None or value == "":
            # Clear if empty to allow environmental fallback in get_settings() if applicable
            # but here we return specific default or DEFAULTS.
            value = self._get_env_fallback(key)
            if value is None or value == "":
                value = str(default) if default is not None else self.DEFAULTS.get(key, "")

        # 5. Normalization (Model names etc.)
        return normalize_model_name(key, value)

    def _get_env_fallback(self, key: str) -> Optional[str]:
        """Maps settings keys to pydantic-settings env vars."""
        env_map = {
            "gemini_api_key": env_settings.GEMINI_API_KEY,
            "openai_api_key": env_settings.OPENAI_API_KEY,
            "cohere_api_key": env_settings.COHERE_API_KEY,
            "mistral_api_key": env_settings.MISTRAL_API_KEY,
            "embedding_provider": env_settings.EMBEDDING_PROVIDER,
            "gemini_transcription_model": env_settings.GEMINI_TRANSCRIPTION_MODEL,
            "gemini_chat_model": env_settings.GEMINI_CHAT_MODEL,
            "gemini_embedding_model": env_settings.GEMINI_EMBEDDING_MODEL,
            "ollama_base_url": env_settings.OLLAMA_BASE_URL,
            "ollama_embedding_model": env_settings.OLLAMA_EMBEDDING_MODEL,
            "local_extraction_model": env_settings.LOCAL_EXTRACTION_MODEL,
            "local_extraction_url": env_settings.LOCAL_EXTRACTION_URL,
            "qdrant_api_key": env_settings.QDRANT_API_KEY,
            "rerank_provider": env_settings.RERANKER_PROVIDER,
            "local_rerank_model": env_settings.LOCAL_RERANK_MODEL,
        }
        return env_map.get(key)

    async def update_setting(self, key: str, value: str, group: str = "general", is_secret: bool = False) -> Setting:
        """
        Atomic update of a setting and its corresponding cache.
        """
        if self.repository is None:
            raise TechnicalError("Cannot update setting without database session.")

        log_val = "********" if is_secret else value
        print(f"DEBUG: update_setting called for {key} with value='{value}'")
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
            raise TechnicalError(f"Database error updating setting: {key}")

    async def update_settings_batch(self, updates: List[Dict[str, Any]]) -> List[Setting]:
        """
        Batch update settings in a single transaction.
        Updates internal cache after successful commit.
        """
        if self.db is None or self.repository is None:
            raise TechnicalError("Database session required for batch update.")

        updated_settings = []
        try:
            for upd_data in updates:
                key = upd_data["key"]
                value = upd_data.get("value")
                print(f"DEBUG BATCH: key={key}, value={value}")
                group = upd_data.get("group", "general")
                is_secret = upd_data.get("is_secret", False)

                # Fetch current
                setting = await self.repository.get_by_key(key)

                if not setting:
                    # Create new (handle None as empty string)
                    val_to_save = value if value is not None else ""
                    setting = await self.repository.create(
                        {"key": key, "value": val_to_save, "group": group, "is_secret": is_secret}
                    )
                else:
                    # Protection against overwriting with masked placeholder
                    if is_secret and value == "********":
                        updated_settings.append(setting)
                        continue

                    # Update ORM object
                    # FIX: Allow clearing setting if value is explicitly None (from frontend)
                    if "value" in upd_data:
                        setting.value = value if value is not None else ""

                    if "group" in upd_data:
                        setting.group = upd_data["group"]
                    if "is_secret" in upd_data:
                        setting.is_secret = upd_data["is_secret"]

                    self.db.add(setting)

                updated_settings.append(setting)

            await self.db.commit()

            # Refresh and Update Cache
            async with self.__class__._cache_lock:
                for s in updated_settings:
                    await self.db.refresh(s)
                    self.__class__._cache[s.key] = s.value

            return updated_settings

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch update failed: {e}", exc_info=True)
            raise TechnicalError(f"Failed to update settings batch: {e}")

    async def seed_defaults(self) -> None:
        """
        Seeds missing default settings using optimized batching.
        Fixes P1: N+1 Seeding pattern.
        """
        if self.repository is None or self.db is None:
            raise TechnicalError("Cannot seed settings without database session.")

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
        if self.repository is None:
            return []
        return await self.repository.get_all(limit=1000)


async def get_settings_service(db: Annotated[AsyncSession, Depends(get_db)]) -> SettingsService:
    """Dependency Provider."""
    return SettingsService(db)
