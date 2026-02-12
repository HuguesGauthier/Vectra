import pytest
from app.core.utils.model_normalization import normalize_model_name


def test_normalize_model_name_gemini_embedding():
    # Happy Path: Gemini embedding model needs prefix
    assert normalize_model_name("gemini_embedding_model", "text-embedding-004") == "models/text-embedding-004"
    assert normalize_model_name("GEMINI_EMBEDDING", "embedding-001") == "models/embedding-001"

    # Already prefixed
    assert normalize_model_name("gemini_embedding_model", "models/text-embedding-004") == "models/text-embedding-004"

    # Complex path (should not prefix)
    assert (
        normalize_model_name("gemini_embedding_model", "tunedModels/my-custom-model") == "tunedModels/my-custom-model"
    )


def test_normalize_model_name_gemini_chat():
    # Chat models should NOT have prefix
    assert normalize_model_name("gemini_chat_model", "gemini-1.5-flash-latest") == "gemini-1.5-flash-latest"
    assert normalize_model_name("gemini_chat_model", "gemini-2.0-flash-exp") == "gemini-2.0-flash-exp"


def test_normalize_model_name_others():
    # Non-Gemini models should NOT be touched
    assert normalize_model_name("openai_embedding_model", "text-embedding-3-small") == "text-embedding-3-small"
    assert normalize_model_name("local_embedding_model", "nomic-embed-text") == "nomic-embed-text"


def test_normalize_model_name_edge_cases():
    # Keys with 'key' (like api_key) should not trigger normalization
    assert normalize_model_name("gemini_api_key", "AIza...") == "AIza..."

    # Edge cases: None, Empty, Non-string
    assert normalize_model_name("gemini_embedding_model", "") == ""
    assert normalize_model_name("gemini_embedding_model", None) is None
    assert normalize_model_name("gemini_embedding_model", 123) == 123
