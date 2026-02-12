import pytest

from app.core.pricing_defaults import EMBEDDING_PRICES, GENERATIVE_PRICES, MODEL_PRICES


class TestPricingDefaults:
    """Verify pricing configuration integrity."""

    def test_constants_structure(self):
        """Ensure constants are properly typed dictionaries."""
        assert isinstance(EMBEDDING_PRICES, dict)
        assert isinstance(GENERATIVE_PRICES, dict)
        assert isinstance(MODEL_PRICES, dict)

    def test_merged_dictionary_integrity(self):
        """MODEL_PRICES should contain all keys from others."""
        for key in EMBEDDING_PRICES:
            assert key in MODEL_PRICES
            assert MODEL_PRICES[key] == EMBEDDING_PRICES[key]

        for key in GENERATIVE_PRICES:
            assert key in MODEL_PRICES
            assert MODEL_PRICES[key] == GENERATIVE_PRICES[key]

    def test_specific_model_pricing(self):
        """Verify key models have pricing defined."""
        required_models = [
            "models/text-embedding-004",
            "gemini-1.5-flash",
            "gpt-4o",
            "mistral-large-latest",
            "ollama",
        ]
        for model in required_models:
            assert model in MODEL_PRICES
            assert MODEL_PRICES[model] >= 0

    def test_pricing_values_sanity(self):
        """Ensure no negative prices or absurdly high values."""
        for model, price in MODEL_PRICES.items():
            assert price >= 0, f"Price for {model} cannot be negative"
            assert price < 1.0, f"Price for {model} seems too high (> 1.0 USD per 1k tokens)"

    def test_default_fallback(self):
        """Default key should exist."""
        assert "default" in MODEL_PRICES
        assert MODEL_PRICES["default"] > 0
