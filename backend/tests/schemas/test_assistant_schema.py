"""
Tests for Assistant Schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.assistant import MAX_CONNECTORS, AIModel, AssistantBase, AssistantCreate, AssistantUpdate


def test_assistant_base_defaults():
    a = AssistantBase(name="Test Bot")
    assert a.model == AIModel.GPT_4O
    assert a.top_k_retrieval == 25
    assert a.configuration.temperature == 0.7


def test_assistant_validation_model():
    with pytest.raises(ValidationError) as exc:
        AssistantCreate(name="Fail", model="invalid-model")
    assert "gpt-4o" in str(exc.value)
    assert "gpt-4o-mini" in str(exc.value)


def test_assistant_top_n_logic():
    # Success
    a = AssistantCreate(name="OK", top_k_retrieval=10, top_n_rerank=5)
    assert a.top_n_rerank == 5

    # Failure
    with pytest.raises(ValidationError) as exc:
        AssistantCreate(name="Fail", top_k_retrieval=5, top_n_rerank=10)
    assert "cannot be > top_k_retrieval" in str(exc.value)


def test_assistant_update_partial():
    u = AssistantUpdate(name="New Name")
    assert u.description is None
    assert u.model is None  # Partial


def test_assistant_dos_protection_connectors():
    """P0: Verify that we cannot link too many connectors."""
    too_many_ids = [uuid4() for _ in range(MAX_CONNECTORS + 1)]
    with pytest.raises(ValidationError) as exc:
        AssistantCreate(name="DoS", linked_connector_ids=too_many_ids)
    assert "List should have at most" in str(exc.value)


def test_assistant_config_validation():
    """Verify structured config validation."""
    # Valid
    a = AssistantCreate(name="Config", configuration={"temperature": 1.5})
    assert a.configuration.temperature == 1.5

    # Invalid (too high)
    with pytest.raises(ValidationError) as exc:
        AssistantCreate(name="Fail", configuration={"temperature": 2.5})
    assert "Input should be less than or equal to 2" in str(exc.value)
