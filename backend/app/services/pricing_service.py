import logging
from typing import Annotated

from fastapi import Depends

from app.core.pricing_defaults import MODEL_PRICES
from app.schemas.pricing import PricingMapResponse
from app.services.settings_service import SettingsService, get_settings_service

logger = logging.getLogger(__name__)


class PricingService:
    """
    Architect Refactor of PricingService.
    Supports async resolution (P1) and proper DI (P1).
    """

    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service


    async def get_pricing_map(self) -> PricingMapResponse:
        """
        Returns a dictionary of model names to price per 1k tokens.
        Ensures a safe fallback to defaults in case of configuration errors.
        """
        # Start with static defaults
        prices = MODEL_PRICES.copy()

        try:
            # Async resolution of settings
            local_model = await self.settings_service.get_value("local_embedding_model")

            if local_model and isinstance(local_model, str):
                prices[local_model] = 0.0

            return PricingMapResponse(prices=prices)

        except Exception as e:
            logger.error(f"Failed to calculate pricing map, using defaults: {e}", exc_info=True)
            # Return current state of 'prices' (which contains defaults) to avoid breaking UI
            return PricingMapResponse(prices=prices)

    def calculate_cost(
        self,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        is_cached: bool = False,
    ) -> float:
        """
        Calculates the estimated cost of a transaction in USD.

        Args:
            provider: The LLM provider (e.g. 'openai', 'gemini', 'ollama').
            model_name: The specific model used.
            input_tokens: Number of prompt tokens.
            output_tokens: Number of completion tokens.
            is_cached: Whether the input tokens were cached (affects pricing for some providers).

        Returns:
            float: Estimated cost in USD.
        """
        if not provider:
            return 0.0

        provider = provider.lower().strip()
        model_key = model_name.lower().strip()

        # 1. Free Providers
        if provider in ("ollama", "local", "test"):
            return 0.0

        # 2. Get Price Config
        # We try to match the model name in our price map.
        # If exact match fails, we might need a fallback or partial match (omitted for now to keep it safe).
        base_price_1k = MODEL_PRICES.get(model_key)

        if base_price_1k is None:
            # Try to find a logical fallback or just return 0 to avoid wild guesses?
            # For now, let's log a warning and return 0, or use a default "average"?
            # Instructions said "unknown provider -> 0". 
            # If known provider but unknown model, maybe 0 is safer than wrong data.
            logger.warning(f"PricingService: Unknown model '{model_name}' for provider '{provider}'. Cost = 0.")
            return 0.0

        # 3. Calculate
        # NOTE: MODEL_PRICES currently has a single float per 1k tokens (blended or input-only).
        # Real pricing is (Input * Price_In) + (Output * Price_Out).
        # The existing 'MODEL_PRICES' in `pricing_defaults.py` seems to be a single float per model.
        # Let's check `pricing_defaults.py` content again.
        # It says: "Generative prices below represent estimated blended costs or input-only costs used for rough budgetary tracking".
        # So we will use this simplified metric for now as requested.
        
        # If we want to be more precise in the future, we need to expand MODEL_PRICES structure.
        # For now: Cost = (Total Tokens / 1000) * Price_Per_1k
        
        total_tokens = input_tokens + output_tokens
        
        # Handle Caching (Gemini/Anthropic specific logic could go here)
        # For this iteration, if cached, maybe we discount the input? 
        # But we only have a blended price. 
        # Let's just apply the standard calc for now unless we change the constant structure.
        
        cost = (total_tokens / 1000.0) * base_price_1k
        return round(cost, 6)


async def get_pricing_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> PricingService:
    """Dependency provider for PricingService."""
    return PricingService(settings_service)
