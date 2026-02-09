"""
Tests for Assistant model validation.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.assistant import (MAX_TOP_K, MAX_TOP_N, MIN_TOP_K, MIN_TOP_N,
                                   AssistantBase, AssistantCreate,
                                   AssistantUpdate)


class TestAssistantValidation:
    """Test validation rules."""

    def test_valid_assistant_creation(self):
        """Valid assistant should pass validation."""
        assistant = AssistantCreate(
            name="Test Assistant",
            description="Test description",
            instructions="Custom instructions",
            model="gpt-4o",
            top_k_retrieval=25,
            top_n_rerank=5,
        )
        assert assistant.name == "Test Assistant"
        assert assistant.top_k_retrieval == 25

    def test_top_k_exceeds_maximum_fails(self):
        """top_k above MAX_TOP_K should fail."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantCreate(name="Test", top_k_retrieval=101)  # Exceeds MAX_TOP_K (100)
        assert "top_k_retrieval" in str(exc_info.value)

    def test_top_k_below_minimum_fails(self):
        """top_k below MIN_TOP_K should fail."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantCreate(name="Test", top_k_retrieval=0)  # Below MIN_TOP_K (1)
        assert "top_k_retrieval" in str(exc_info.value)

    def test_top_n_exceeds_top_k_fails(self):
        """top_n greater than top_k should fail."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantCreate(name="Test", top_k_retrieval=10, top_n_rerank=15)  # Greater than top_k
        # Check for field or general validation failure signal
        err_str = str(exc_info.value)
        assert "top_n_rerank" in err_str or "top_k_retrieval" in err_str

    def test_invalid_model_fails(self):
        """Invalid model name should fail."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantCreate(name="Test", model="invalid-model-xyz")
        # Pydantic will reject invalid Literal value
        assert "model" in str(exc_info.value).lower()

    def test_invalid_configuration_temperature_type_fails(self):
        """Invalid configuration value type should fail."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantCreate(name="Test", configuration={"temperature": "not a number"})
        # Pydantic V2 error message for float parsing
        assert "configuration" in str(exc_info.value)

    def test_empty_name_fails(self):
        """Empty name should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantCreate(name="")
        assert "name" in str(exc_info.value).lower()

    def test_valid_configuration(self):
        """Valid configuration should pass."""
        assistant = AssistantCreate(name="Test", configuration={"temperature": 0.7, "max_tokens": 1000})
        # Access via dot notation if it is a model, or dict if dict.
        # Validating type first to be safe, but assuming object based on error.
        try:
            assert assistant.configuration["temperature"] == 0.7
        except TypeError:
            # Fallback to dot notation
            assert assistant.configuration.temperature == 0.7


class TestAssistantUpdate:
    """Test update schema."""

    def test_partial_update_valid(self):
        """Partial updates should be valid."""
        update = AssistantUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.model is None  # Other fields remain None

    def test_update_with_invalid_constraints_fails(self):
        """Update with invalid values should fail."""
        with pytest.raises(ValidationError) as exc_info:
            AssistantUpdate(top_k_retrieval=0)  # Below minimum
        assert "top_k_retrieval" in str(exc_info.value)

    def test_update_with_valid_model(self):
        """Update with valid model should work."""
        update = AssistantUpdate(model="gemini-1.5-flash")
        assert update.model == "gemini-1.5-flash"

    def test_update_with_valid_reranker(self):
        """Update with valid reranker should work."""
        update = AssistantUpdate(reranker_provider="cohere")
        assert update.reranker_provider == "cohere"
