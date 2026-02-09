from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.pricing_defaults import MODEL_PRICES
from app.schemas.pricing import PricingMapResponse
from app.services.pricing_service import PricingService


@pytest.fixture
def mock_settings_service():
    return AsyncMock()


@pytest.fixture
def pricing_service(mock_settings_service):
    return PricingService(mock_settings_service)


@pytest.mark.asyncio
async def test_get_pricing_map_success(pricing_service, mock_settings_service):
    """Verify that pricing map is correctly calculated with local model override."""
    # Setup mock
    mock_settings_service.get_value.return_value = "local-model"

    # Execute
    result = await pricing_service.get_pricing_map()

    # Verify
    assert isinstance(result, PricingMapResponse)
    assert result.prices["local-model"] == 0.0
    # Ensure some default exists
    assert "models/text-embedding-004" in result.prices
    assert result.prices["models/text-embedding-004"] == MODEL_PRICES["models/text-embedding-004"]


@pytest.mark.asyncio
async def test_get_pricing_map_fallback(pricing_service, mock_settings_service):
    """Verify that service returns defaults even if settings fails."""
    # Setup mock to raise exception
    mock_settings_service.get_value.side_effect = Exception("DB Timeout")

    # Execute
    result = await pricing_service.get_pricing_map()

    # Verify (Safe Fallback)
    assert isinstance(result, PricingMapResponse)
    assert "models/text-embedding-004" in result.prices
    assert result.prices["models/text-embedding-004"] == MODEL_PRICES["models/text-embedding-004"]
