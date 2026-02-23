import re


def normalize_model_name(key: str, value: str) -> str:
    """
    Ensures model names follow expected formats.
    ONLY adds 'models/' prefix for Gemini EMBEDDING models, not chat models.
    """
    if not value or not isinstance(value, str):
        return value

    value = value.strip()
    key_lower = key.lower()
    value_lower = value.lower()

    # Gemini specific normalization
    # CRITICAL: Only add "models/" prefix for EMBEDDING models, not chat models
    if "gemini" in key_lower and not key_lower.endswith("key"):
        is_embedding = "embedding" in key_lower or "embedding" in value_lower

        if is_embedding and not value.startswith("models/") and "/" not in value:
            return f"models/{value}"

    return value
