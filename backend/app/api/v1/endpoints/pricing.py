import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.exceptions import TechnicalError
from app.schemas.pricing import PricingMapResponse
from app.services.pricing_service import PricingService, get_pricing_service

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PricingMapResponse, summary="Get current model pricing")
async def get_pricing(
    service: Annotated[PricingService, Depends(get_pricing_service)],
) -> PricingMapResponse:
    """
    Returns the current pricing configuration for models (embeddings and generative).

    Prices are in USD per 1000 tokens.

    Args:
        service: The pricing service instance injected by FastAPI.

    Returns:
        PricingMapResponse: A dictionary containing the pricing for different models.

    Raises:
        TechnicalError: If there's an error retrieving the pricing configuration.
    """
    try:
        return await service.get_pricing_map()

    except Exception as e:
        logger.error(f"❌ FAIL | get_pricing | Error: {str(e)}", exc_info=True)
        raise TechnicalError(
            message=f"Failed to retrieve pricing: {e}",
            error_code="PRICING_FETCH_ERROR",
        )
