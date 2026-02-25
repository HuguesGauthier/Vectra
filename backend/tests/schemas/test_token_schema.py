"""
Tests for Token Schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.token import Token, TokenPayload


def test_token_valid():
    t = Token(access_token="abc", token_type="bearer")
    assert t.token_type == "bearer"

    # Default behavior
    t2 = Token(access_token="xyz")
    assert t2.token_type == "bearer"


def test_token_invalid_type():
    with pytest.raises(ValidationError) as exc:
        Token(access_token="abc", token_type="mac")
    assert "Input should be 'bearer'" in str(exc.value)


def test_token_payload():
    p = TokenPayload(sub="123", exp=10000)
    assert p.sub == "123"
    assert p.type == "access"
