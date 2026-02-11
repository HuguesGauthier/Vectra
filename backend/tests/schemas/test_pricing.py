import pytest
from app.schemas.pricing import PricingMapResponse


def test_pricing_map_response_structure():
    """Test PricingMapResponse basic structure."""
    response = PricingMapResponse(prices={"gpt-4": 0.03, "gpt-3.5-turbo": 0.002, "gemini-pro": 0.00025})
    assert response.prices["gpt-4"] == 0.03
    assert response.prices["gpt-3.5-turbo"] == 0.002
    assert response.prices["gemini-pro"] == 0.00025
    assert response.currency == "USD"


def test_pricing_map_response_default_currency():
    """Test default currency is USD."""
    response = PricingMapResponse(prices={"model-1": 0.01})
    assert response.currency == "USD"


def test_pricing_map_response_custom_currency():
    """Test custom currency."""
    response = PricingMapResponse(prices={"model-1": 0.01}, currency="EUR")
    assert response.currency == "EUR"


def test_pricing_map_response_empty_prices():
    """Test with empty prices dictionary."""
    response = PricingMapResponse(prices={})
    assert response.prices == {}
    assert response.currency == "USD"


def test_pricing_map_response_required_prices():
    """Test that prices field is required."""
    with pytest.raises(ValueError):
        PricingMapResponse()
