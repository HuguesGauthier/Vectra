from typing import Dict

from pydantic import BaseModel, Field


class PricingMapResponse(BaseModel):
    """
    Response schema for model pricing information.
    """

    prices: Dict[str, float] = Field(..., description="Mapping of model names to price per 1k tokens")
    currency: str = Field(default="USD", description="Currency code")
