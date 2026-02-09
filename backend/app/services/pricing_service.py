import logging
from typing import Annotated, Dict

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
        Fixes P0: Sync context mismatch and P1 raw dict return.
        """
        try:
            # Start with static defaults
            prices = MODEL_PRICES.copy()

            # P0 Fix: Async resolution of settings
            local_model = await self.settings_service.get_value("local_embedding_model")

            if local_model:
                prices[local_model] = 0.0

            return PricingMapResponse(prices=prices)

        except Exception as e:
            logger.error(f"Failed to calculate pricing map: {e}", exc_info=True)
            # Return defaults at minimum to avoid breaking UI (Safe Fallback)
            return PricingMapResponse(prices=MODEL_PRICES.copy())


async def get_pricing_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> PricingService:
    """Dependency provider for PricingService."""
    return PricingService(settings_service)
