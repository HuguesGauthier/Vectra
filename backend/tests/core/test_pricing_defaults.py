import pytest

from app.core.model_catalog import (
    SUPPORTED_CHAT_MODELS,
    EMBEDDING_MODELS,
    get_model_pricing,
    build_pricing_map,
)


class TestModelCatalog:
    """Verify model catalog data integrity and helpers."""

    def test_all_chat_models_have_required_fields(self):
        """Every chat model entry must have id, name, description, category, input_price, output_price."""
        required_keys = {"id", "name", "description", "category", "input_price", "output_price"}
        for provider, models in SUPPORTED_CHAT_MODELS.items():
            assert len(models) > 0, f"Provider '{provider}' has no models"
            for m in models:
                for key in required_keys:
                    assert key in m, f"Model {m.get('id', '?')} missing key '{key}'"

    def test_embedding_models_have_required_fields(self):
        """Embedding models need id, name, input_price, output_price."""
        for model_id, m in EMBEDDING_MODELS.items():
            assert m["id"] == model_id
            assert "input_price" in m
            assert m["output_price"] == 0.0

    def test_pricing_values_are_non_negative(self):
        """No negative prices anywhere."""
        for models in SUPPORTED_CHAT_MODELS.values():
            for m in models:
                assert m["input_price"] >= 0, f"{m['id']} input_price is negative"
                assert m["output_price"] >= 0, f"{m['id']} output_price is negative"

        for _, m in EMBEDDING_MODELS.items():
            assert m["input_price"] >= 0

    def test_get_model_pricing_chat(self):
        """Should find a known chat model."""
        result = get_model_pricing("gemini-2.0-flash")
        assert result is not None
        input_p, output_p = result
        assert input_p > 0
        assert output_p > 0

    def test_get_model_pricing_embedding(self):
        """Should find a known embedding model."""
        result = get_model_pricing("text-embedding-3-small")
        assert result is not None
        input_p, output_p = result
        assert input_p > 0
        assert output_p == 0.0

    def test_get_model_pricing_unknown(self):
        """Should return None for an unknown model."""
        assert get_model_pricing("nonexistent-model-9000") is None

    def test_build_pricing_map_contains_key_models(self):
        """Pricing map should contain all known models plus free providers."""
        prices = build_pricing_map()
        assert "gemini-2.0-flash" in prices
        assert "gpt-5" in prices
        assert "mistral-large-latest" in prices
        assert "text-embedding-3-small" in prices
        assert "ollama" in prices
        assert prices["ollama"] == 0.0
        assert prices["local"] == 0.0
        assert "default" in prices

    def test_build_pricing_map_values_are_sane(self):
        """Blended per-1K values should be small positive numbers."""
        prices = build_pricing_map()
        for model, price in prices.items():
            assert price >= 0, f"Price for {model} is negative"
            assert price < 1.0, f"Price for {model} seems too high (> $1.0 per 1K tokens)"
