"""Token estimation utilities for RAG pipeline analytics.

Provides simple token estimation based on word count when exact token counts
are not available from LLM providers.
"""


def estimate_tokens(text: str) -> int:
    """Estimate token count from text.

    Uses a simple heuristic: ~1.3 tokens per word.
    This works reasonably well for English and French text.

    Args:
        text: Input text to estimate tokens for.

    Returns:
        Estimated number of tokens.

    Note:
        This is an approximation. Actual token counts may vary by ±15-20%
        depending on the tokenizer used (GPT, Gemini, etc.).
    """
    if not text or not isinstance(text, str):
        return 0
    return int(len(text.split()) * 1.3)
