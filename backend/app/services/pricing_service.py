import logging
from typing import Annotated

from fastapi import Depends

from app.core.model_catalog import get_model_pricing, build_pricing_map
from app.schemas.pricing import PricingMapResponse
from app.services.settings_service import SettingsService, get_settings_service

logger = logging.getLogger(__name__)


class PricingService:
    """
    Calculates LLM usage costs using the centralized model catalog.
    Uses separate input/output pricing for accurate cost estimation.
    """

    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service

    async def get_pricing_map(self) -> PricingMapResponse:
        """
        Returns a dictionary of model names to price per 1k tokens.
        Used by the frontend dashboard for cost visualization.
        """
        prices = build_pricing_map()

        try:
            local_model = await self.settings_service.get_value("local_embedding_model")
            if local_model and isinstance(local_model, str):
                prices[local_model] = 0.0

            return PricingMapResponse(prices=prices)

        except Exception as e:
            logger.error(f"Failed to calculate pricing map, using defaults: {e}", exc_info=True)
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
        Uses separate input/output pricing from the model catalog for accuracy.

        Args:
            provider: The LLM provider (e.g. 'openai', 'gemini', 'ollama').
            model_name: The specific model used.
            input_tokens: Number of prompt tokens.
            output_tokens: Number of completion tokens.
            is_cached: Whether the input tokens were cached.

        Returns:
            float: Estimated cost in USD.
        """
        if not provider:
            return 0.0

        provider = provider.lower().strip()

        # Free providers
        if provider in ("ollama", "local", "test"):
            return 0.0

        if not model_name:
            return 0.0

        model_key = model_name.lower().strip()

        # Look up pricing from central catalog
        pricing = get_model_pricing(model_key)

        if pricing is None:
            logger.warning(f"PricingService: Unknown model '{model_name}' for provider '{provider}'. Cost = 0.")
            return 0.0

        input_price_per_1m, output_price_per_1m = pricing

        # cost = (input_tokens × input_price / 1M) + (output_tokens × output_price / 1M)
        cost = (input_tokens * input_price_per_1m / 1_000_000.0) + (output_tokens * output_price_per_1m / 1_000_000.0)

        return round(cost, 8)


async def get_pricing_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> PricingService:
    """Dependency provider for PricingService."""
    return PricingService(settings_service)
