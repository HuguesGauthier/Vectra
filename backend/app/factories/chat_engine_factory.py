import logging
from typing import Any

from app.models.assistant import Assistant
from app.services.chat.utils import LLMFactory
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

        Args:
            assistant: The assistant model containing provider info
            settings_service: Service to retrieve global settings (API keys, model versions)
            **kwargs: Additional arguments to pass to LLMFactory (e.g. temperature, output_class)

        Returns:
            Configured LLM instance
        """
        # 1. Determine Provider from Assistant
        provider = assistant.model_provider

        # 2. Fetch specific configuration from Global Settings
        # Assistant.model enum currently determines the provider,
        # but the specific model version is stored in settings.
        model_key = f"{provider}_chat_model"
        api_key_key = f"{provider}_api_key"

        model_name = await settings_service.get_value(model_key)
        api_key = await settings_service.get_value(api_key_key)

        if not model_name:
            logger.warning(f"No model configured for provider {provider} (key={model_key}). Using default.")
            # Fallback handling could be added here if needed,
            # currently LLMFactory might handle or fail on empty model depending on implementation

        logger.debug(f"[ChatEngineFactory] Creating engine: provider={provider}, model={model_name}")

        # 3. Create LLM via Utilities
        return LLMFactory.create_llm(provider, model_name, api_key, **kwargs)

    @staticmethod
    async def create_from_provider(provider: str, settings_service: SettingsService, **kwargs) -> Any:
        """
        Creates a configured LLM instance for a specific provider.
        Useful for services (like Vanna) that don't have an Assistant object but know the provider.
        """
        model_key = f"{provider}_chat_model"
        api_key_key = f"{provider}_api_key"

        model_name = await settings_service.get_value(model_key)
        api_key = await settings_service.get_value(api_key_key)

        if not model_name:
            logger.warning(f"No model configured for provider {provider} (key={model_key}). Using default.")

        logger.debug(f"[ChatEngineFactory] Creating engine from provider: provider={provider}, model={model_name}")

        return LLMFactory.create_llm(provider, model_name, api_key, **kwargs)
