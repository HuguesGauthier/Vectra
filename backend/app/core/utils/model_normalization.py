import re


def normalize_model_name(key: str, value: str) -> str:
    """
    Ensures model names follow expected formats.
    ONLY adds 'models/' prefix for Gemini EMBEDDING models, not chat models.
    """
    if not value or not isinstance(value, str):
        return value

    value = value.strip()

    # Gemini specific normalization
    # CRITICAL: Only add "models/" prefix for EMBEDDING models, not chat models
    # Chat models: gemini-1.5-flash-latest, gemini-2.0-flash-exp (NO prefix)
    # Embedding models: text-embedding-004, embedding-001 (WITH models/ prefix)
    if "gemini" in key.lower() and not key.lower().endswith("key"):
        # Only add prefix for embedding models
        if "embedding" in key.lower() or "embedding" in value.lower():
            if value and not value.startswith("models/"):
                # Don't prefix if it's already a complex path
                if "/" not in value:
                    return f"models/{value}"

    return value
