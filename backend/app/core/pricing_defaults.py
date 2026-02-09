from typing import Dict, Final

"""
Default pricing configuration.
Prices are in USD per 1,000 tokens (estimated).
NOTE: These are defaults. Real-time pricing may vary by region or tier.
"""

# --- Embeddings (Cost to Vectorize) ---
EMBEDDING_PRICES: Final[Dict[str, float]] = {
    # Gemini
    "models/text-embedding-004": 0.000025,
    "models/text-embedding-005": 0.000025,
    "models/gemini-embedding-001": 0.000025,
    # OpenAI
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
    "text-embedding-ada-002": 0.00010,
}

# --- Generative (LLM Inference) ---
# Note: Usually separates Input/Output cost.
# These look like blended or input-only estimates.
GENERATIVE_PRICES: Final[Dict[str, float]] = {
    # Gemini

    "gemini-2.0-flash": 0.00001875,
    "gemini-1.5-flash": 0.00001875,
    "gemini-1.5-pro": 0.00125,
    # OpenAI
    "gpt-4o": 0.00250,
    "gpt-4o-mini": 0.00015,
    "gpt-4": 0.03,
    "gpt-4-turbo": 0.01,
    "gpt-3.5-turbo": 0.0005,
}

# --- Combined Access ---
# Merged dictionary for O(1) lookups by model name
MODEL_PRICES: Final[Dict[str, float]] = {
    **EMBEDDING_PRICES,
    **GENERATIVE_PRICES,
    # Fallback / Local
    "default": 0.00010,
}
