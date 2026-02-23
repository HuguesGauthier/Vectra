import pytest
from unittest.mock import AsyncMock
from app.services.pricing_service import PricingService
from app.schemas.pricing import PricingMapResponse
from app.core.model_catalog import build_pricing_map


@pytest.fixture
def mock_settings_service():
    return AsyncMock()


@pytest.fixture
def service(mock_settings_service):
    return PricingService(mock_settings_service)


@pytest.mark.asyncio
async def test_get_pricing_map_success(service, mock_settings_service):
    local_model = "snowflake/snowflake-arctic-embed-m"
    mock_settings_service.get_value.return_value = local_model

    result = await service.get_pricing_map()

    assert isinstance(result, PricingMapResponse)
    assert result.prices[local_model] == 0.0
    assert "gemini-2.0-flash" in result.prices
    expected_prices = build_pricing_map()
    assert result.prices["gemini-2.0-flash"] == expected_prices["gemini-2.0-flash"]


@pytest.mark.asyncio
async def test_get_pricing_map_no_local_model(service, mock_settings_service):
    mock_settings_service.get_value.return_value = None

    result = await service.get_pricing_map()

    expected = build_pricing_map()
    assert result.prices == expected
    assert result.currency == "USD"


@pytest.mark.asyncio
async def test_get_pricing_map_fallback_on_error(service, mock_settings_service):
    mock_settings_service.get_value.side_effect = Exception("DB Timeout")

    result = await service.get_pricing_map()

    expected = build_pricing_map()
    assert result.prices == expected
    mock_settings_service.get_value.assert_called_once_with("local_embedding_model")


def test_calculate_cost_known_model(service):
    """Gemini 2.0 Flash: input $0.10/1M, output $0.40/1M"""
    cost = service.calculate_cost(
        provider="gemini",
        model_name="gemini-2.0-flash",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # (1M * 0.10 / 1M) + (1M * 0.40 / 1M) = 0.10 + 0.40 = 0.50
    assert cost == pytest.approx(0.50, abs=0.001)


def test_calculate_cost_unknown_model(service):
    """Unknown model returns 0."""
    cost = service.calculate_cost(
        provider="openai",
        model_name="unknown-model",
        input_tokens=1000,
        output_tokens=1000,
    )
    assert cost == 0.0


def test_calculate_cost_free_provider(service):
    """Ollama/local always return 0."""
    cost = service.calculate_cost(
        provider="ollama",
        model_name="llama3",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    assert cost == 0.0


def test_calculate_cost_no_provider(service):
    """Empty provider returns 0."""
    cost = service.calculate_cost(
        provider="",
        model_name="gpt-4o",
        input_tokens=1000,
        output_tokens=1000,
    )
    assert cost == 0.0
