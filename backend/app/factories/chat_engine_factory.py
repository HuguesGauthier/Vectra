import logging
from typing import Any, Tuple

from app.models.assistant import Assistant
from app.factories.llm_factory import LLMFactory
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class ChatEngineFactory:
    """
    Factory to create Chat Engine instances based on Assistant configuration.
    Centralizes logic for retrieving provider, model version, and API keys from Settings.
    """

    @staticmethod
    async def create_from_assistant(assistant: Assistant, settings_service: SettingsService, **kwargs) -> Any:
        """
        Creates a configured LLM instance for the given assistant.
        """
        provider = assistant.model_provider
        model_name, api_key = await ChatEngineFactory._get_config(provider, settings_service)

        logger.debug(f"[ChatEngineFactory] Creating engine: provider={provider}, model={model_name}")
        return LLMFactory.create_llm(provider, model_name, api_key, **kwargs)

    @staticmethod
    async def create_from_provider(provider: str, settings_service: SettingsService, **kwargs) -> Any:
        """
        Creates a configured LLM instance for a specific provider.
        Useful for services (like Vanna) that don't have an Assistant object but know the provider.
        """
        model_name, api_key = await ChatEngineFactory._get_config(provider, settings_service)

        logger.debug(f"[ChatEngineFactory] Creating engine from provider: provider={provider}, model={model_name}")
        return LLMFactory.create_llm(provider, model_name, api_key, **kwargs)

    @staticmethod
    async def _get_config(provider: str, settings_service: SettingsService) -> Tuple[str, str]:
        """
        Helper to fetch specific configuration from Global Settings.
        """
        model_key = f"{provider}_chat_model"
        api_key_key = f"{provider}_api_key"

        model_name = await settings_service.get_value(model_key)
        api_key = await settings_service.get_value(api_key_key)

        if not model_name:
            logger.warning(f"No model configured for provider {provider} (key={model_key}).")

        return model_name, api_key
