import pytest
from uuid import uuid4
from datetime import datetime, timezone
from app.models.assistant import Assistant, AssistantConnectorLink
from app.schemas.assistant import AIModel, AssistantConfig


def test_assistant_defaults():
    """Test default values for Assistant model."""
    assistant = Assistant(name="Test Assistant", model=AIModel.GEMINI)

    assert assistant.is_enabled is True
    assert assistant.user_authentication is False
    assert assistant.use_reranker is False
    assert assistant.top_k_retrieval == 25
    assert assistant.top_n_rerank == 5
    assert isinstance(assistant.configuration, dict)

    assert assistant.created_at is not None


def test_model_provider_logic():
    """Test logic for deriving provider from model name."""

    # helper
    def create_assist(model_enum):
        return Assistant(name="Test", model=model_enum)

    # Gemini
    a = create_assist(AIModel.GEMINI)
    assert a.model_provider == "gemini"

    # OpenAI
    a = create_assist(AIModel.OPENAI)
    assert a.model_provider == "openai"

    # Mistral
    a = create_assist(AIModel.MISTRAL)
    assert a.model_provider == "mistral"

    # Ollama
    a = create_assist(AIModel.OLLAMA)
    assert a.model_provider == "ollama"


def test_assistant_connector_link_structure():
    """Test the link model instantiation."""
    aid = uuid4()
    cid = uuid4()
    link = AssistantConnectorLink(assistant_id=aid, connector_id=cid)

    assert link.assistant_id == aid
    assert link.connector_id == cid


def test_assistant_config_serialization():
    """Test configuration field handling."""
    config = AssistantConfig(temperature=0.5)
    # SQLModel stores dict in JSONB
    assistant = Assistant(name="Test", model=AIModel.GEMINI, configuration=config.model_dump())

    assert assistant.configuration["temperature"] == 0.5
