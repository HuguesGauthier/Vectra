import pytest
from app.core.rag.utils import estimate_tokens


def test_estimate_tokens_happy_path():
    # "~1.3 tokens per word"
    # "Hello world" = 2 words * 1.3 = 2.6 -> int(2.6) = 2
    assert estimate_tokens("Hello world") == 2

    # "The quick brown fox jumps over the lazy dog" = 9 words * 1.3 = 11.7 -> int(11.7) = 11
    assert estimate_tokens("The quick brown fox jumps over the lazy dog") == 11


def test_estimate_tokens_whitespace():
    # Extra whitespace should not affect word count
    assert estimate_tokens("  Hello   world  ") == 2
    assert estimate_tokens("\nHello\n\tworld\t") == 2


def test_estimate_tokens_edge_cases():
    assert estimate_tokens("") == 0
    assert estimate_tokens(None) == 0
    assert estimate_tokens(123) == 0  # Non-string should return 0
    assert estimate_tokens([]) == 0
