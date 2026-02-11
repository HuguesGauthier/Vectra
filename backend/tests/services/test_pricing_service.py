import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.pricing_service import PricingService
from app.schemas.pricing import PricingMapResponse
from app.core.pricing_defaults import MODEL_PRICES


@pytest.fixture
def mock_settings_service():
    return AsyncMock()


@pytest.fixture
def service(mock_settings_service):
    return PricingService(mock_settings_service)


@pytest.mark.asyncio
async def test_get_pricing_map_success(service, mock_settings_service):
    # Setup
    local_model = "snowflake/snowflake-arctic-embed-m"
    mock_settings_service.get_value.return_value = local_model

    # Execute
    result = await service.get_pricing_map()

    # Assert
    assert isinstance(result, PricingMapResponse)
    assert result.prices[local_model] == 0.0
    # Check if a default price is still there
    assert "gemini-1.5-flash" in result.prices
    assert result.prices["gemini-1.5-flash"] == MODEL_PRICES["gemini-1.5-flash"]


@pytest.mark.asyncio
async def test_get_pricing_map_no_local_model(service, mock_settings_service):
    # Setup
    mock_settings_service.get_value.return_value = None

    # Execute
    result = await service.get_pricing_map()

    # Assert
    assert result.prices == MODEL_PRICES
    assert result.currency == "USD"


@pytest.mark.asyncio
async def test_get_pricing_map_fallback_on_error(service, mock_settings_service):
    # Setup
    mock_settings_service.get_value.side_effect = Exception("DB Timeout")

    # Execute
    result = await service.get_pricing_map()

    # Assert
    # Should still return defaults even if settings service fails
    assert result.prices == MODEL_PRICES
    mock_settings_service.get_value.assert_called_once_with("local_embedding_model")
