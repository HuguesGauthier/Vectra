import pytest
from uuid import uuid4
from app.schemas.assistant import AssistantCreate, AssistantUpdate, AssistantConfig, AIModel, MAX_CONNECTORS


def test_assistant_create_defaults():
    """Test default values in AssistantCreate."""
    assistant = AssistantCreate(name="Test Assistant")
    assert assistant.name == "Test Assistant"
    assert assistant.model == AIModel.GPT_4O
    assert assistant.top_k_retrieval == 25
    assert assistant.top_n_rerank == 5
    assert assistant.use_reranker is False
    assert assistant.linked_connector_ids == []


def test_assistant_top_n_validation():
    """Test that top_n cannot exceed top_k."""
    with pytest.raises(ValueError, match="top_n_rerank.*cannot be.*top_k_retrieval"):
        AssistantCreate(name="Test", top_k_retrieval=10, top_n_rerank=15)  # Invalid: exceeds top_k


def test_assistant_top_n_valid():
    """Test valid top_n <= top_k."""
    assistant = AssistantCreate(name="Test", top_k_retrieval=20, top_n_rerank=10)
    assert assistant.top_n_rerank == 10


def test_assistant_config_constraints():
    """Test AssistantConfig field constraints."""
    config = AssistantConfig(temperature=1.5, max_output_tokens=2048)
    assert config.temperature == 1.5
    assert config.max_output_tokens == 2048

    # Test out of range
    with pytest.raises(ValueError):
        AssistantConfig(temperature=3.0)  # > 2.0


def test_assistant_dos_protection():
    """Test MAX_CONNECTORS DoS protection."""
    # Should fail with too many connectors
    with pytest.raises(ValueError):
        AssistantCreate(name="Test", linked_connector_ids=[uuid4() for _ in range(MAX_CONNECTORS + 1)])


def test_assistant_update_partial():
    """Test partial updates with AssistantUpdate."""
    update = AssistantUpdate(name="Updated Name")
    assert update.name == "Updated Name"
    assert update.model is None
    assert update.top_k_retrieval is None


def test_assistant_model_provider_property():
    """Test model_provider property derivation."""
    assistant = AssistantCreate(name="Test", model=AIModel.GEMINI)
    assert assistant.model_provider == "gemini"

    assistant2 = AssistantCreate(name="Test", model=AIModel.OPENAI)
    assert assistant2.model_provider == "openai"


def test_assistant_similarity_cutoff_range():
    """Test similarity cutoff validation."""
    assistant = AssistantCreate(name="Test", similarity_cutoff=0.7)
    assert assistant.similarity_cutoff == 0.7

    with pytest.raises(ValueError):
        AssistantCreate(name="Test", similarity_cutoff=1.5)  # > 1.0
