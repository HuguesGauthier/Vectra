"""
Unit tests for backend/app/schemas/token.py

Tests cover:
- Happy path: Valid token and payload creation
- Edge cases: Optional fields, different token types
- Validation: Missing required fields, invalid types
"""

import pytest
from pydantic import ValidationError

from app.schemas.token import Token, TokenPayload


class TestToken:
    """Test suite for Token schema."""

    # ========== HAPPY PATH ==========

    def test_create_valid_token_with_all_fields(self):
        """Test creating a valid Token with all fields."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "refresh_token": "refresh_token_xyz123",
        }

        token = Token(**data)

        assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "bearer"
        assert token.refresh_token == "refresh_token_xyz123"

    def test_create_token_without_refresh_token(self):
        """Test creating a Token without optional refresh_token."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
        }

        token = Token(**data)

        assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "bearer"
        assert token.refresh_token is None

    def test_create_token_with_default_token_type(self):
        """Test that token_type defaults to 'bearer'."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        }

        token = Token(**data)

        assert token.token_type == "bearer"

    def test_token_model_dump(self):
        """Test serialization of Token to dict."""
        data = {
            "access_token": "access_xyz",
            "token_type": "bearer",
            "refresh_token": "refresh_xyz",
        }

        token = Token(**data)
        dumped = token.model_dump()

        assert dumped == data

    def test_token_model_dump_json(self):
        """Test JSON serialization of Token."""
        data = {
            "access_token": "access_xyz",
            "token_type": "bearer",
        }

        token = Token(**data)
        json_str = token.model_dump_json()

        assert '"access_token":"access_xyz"' in json_str
        assert '"token_type":"bearer"' in json_str

    # ========== EDGE CASES ==========

    def test_create_token_with_very_long_access_token(self):
        """Test creating Token with extremely long JWT."""
        long_jwt = "eyJ" + "a" * 10000 + ".payload.signature"
        data = {
            "access_token": long_jwt,
        }

        token = Token(**data)

        assert token.access_token == long_jwt

    def test_create_token_with_empty_string_access_token(self):
        """Test creating Token with empty string (should succeed - Pydantic allows it)."""
        data = {
            "access_token": "",
        }

        token = Token(**data)

        assert token.access_token == ""

    # ========== VALIDATION ERRORS (WORST CASE) ==========

    def test_missing_access_token_raises_validation_error(self):
        """Test that missing access_token raises ValidationError."""
        data = {
            "token_type": "bearer",
        }

        with pytest.raises(ValidationError) as exc_info:
            Token(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("access_token",)
        assert errors[0]["type"] == "missing"

    def test_invalid_token_type_raises_validation_error(self):
        """Test that invalid token_type (not 'bearer') raises ValidationError."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "invalid",  # Must be 'bearer'
        }

        with pytest.raises(ValidationError) as exc_info:
            Token(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("token_type",)
        # Pydantic v2 uses 'literal_error' for Literal type violations
        assert "literal_error" in errors[0]["type"]

    def test_invalid_access_token_type_raises_validation_error(self):
        """Test that invalid access_token type raises ValidationError."""
        data = {
            "access_token": 12345,  # Should be str
        }

        with pytest.raises(ValidationError) as exc_info:
            Token(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("access_token",)
        assert errors[0]["type"] == "string_type"

    def test_none_access_token_raises_validation_error(self):
        """Test that None access_token raises ValidationError."""
        data = {
            "access_token": None,
        }

        with pytest.raises(ValidationError) as exc_info:
            Token(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("access_token",)


class TestTokenPayload:
    """Test suite for TokenPayload schema."""

    # ========== HAPPY PATH ==========

    def test_create_valid_token_payload_with_all_fields(self):
        """Test creating a valid TokenPayload with all fields."""
        data = {
            "sub": "user-uuid-12345",
            "exp": 1707686400,
            "type": "access",
        }

        payload = TokenPayload(**data)

        assert payload.sub == "user-uuid-12345"
        assert payload.exp == 1707686400
        assert payload.type == "access"

    def test_create_token_payload_with_minimal_fields(self):
        """Test creating TokenPayload with only defaults."""
        payload = TokenPayload()

        assert payload.sub is None
        assert payload.exp is None
        assert payload.type == "access"  # Default value

    def test_create_refresh_token_payload(self):
        """Test creating a refresh token payload."""
        data = {
            "sub": "user-uuid-67890",
            "exp": 1707772800,
            "type": "refresh",
        }

        payload = TokenPayload(**data)

        assert payload.sub == "user-uuid-67890"
        assert payload.exp == 1707772800
        assert payload.type == "refresh"

    def test_token_payload_model_dump(self):
        """Test serialization of TokenPayload to dict."""
        data = {
            "sub": "user-123",
            "exp": 1707686400,
            "type": "access",
        }

        payload = TokenPayload(**data)
        dumped = payload.model_dump()

        assert dumped == data

    def test_token_payload_model_dump_json(self):
        """Test JSON serialization of TokenPayload."""
        data = {
            "sub": "user-456",
            "exp": 1707686400,
            "type": "refresh",
        }

        payload = TokenPayload(**data)
        json_str = payload.model_dump_json()

        assert '"sub":"user-456"' in json_str
        assert '"exp":1707686400' in json_str
        assert '"type":"refresh"' in json_str

    # ========== EDGE CASES ==========

    def test_create_token_payload_with_very_long_sub(self):
        """Test creating TokenPayload with extremely long subject."""
        long_sub = "user-" + "x" * 10000
        data = {
            "sub": long_sub,
        }

        payload = TokenPayload(**data)

        assert payload.sub == long_sub

    def test_create_token_payload_with_negative_exp(self):
        """Test creating TokenPayload with negative expiration (expired token)."""
        data = {
            "sub": "user-123",
            "exp": -1,  # Negative timestamp (expired)
        }

        payload = TokenPayload(**data)

        assert payload.exp == -1

    def test_create_token_payload_with_zero_exp(self):
        """Test creating TokenPayload with zero expiration."""
        data = {
            "sub": "user-123",
            "exp": 0,
        }

        payload = TokenPayload(**data)

        assert payload.exp == 0

    def test_create_token_payload_with_custom_type(self):
        """Test creating TokenPayload with custom token type."""
        data = {
            "sub": "user-123",
            "type": "custom_token_type",
        }

        payload = TokenPayload(**data)

        assert payload.type == "custom_token_type"

    # ========== VALIDATION ERRORS (WORST CASE) ==========

    def test_invalid_sub_type_raises_validation_error(self):
        """Test that invalid sub type raises ValidationError."""
        data = {
            "sub": 12345,  # Should be str
        }

        with pytest.raises(ValidationError) as exc_info:
            TokenPayload(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("sub",)
        assert errors[0]["type"] == "string_type"

    def test_invalid_exp_type_raises_validation_error(self):
        """Test that invalid exp type raises ValidationError."""
        data = {
            "exp": "not-an-int",  # Should be int
        }

        with pytest.raises(ValidationError) as exc_info:
            TokenPayload(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("exp",)
        # Pydantic v2 uses 'int_parsing' for string-to-int conversion errors
        assert errors[0]["type"] == "int_parsing"

    def test_invalid_type_field_type_raises_validation_error(self):
        """Test that invalid type field type raises ValidationError."""
        data = {
            "type": 123,  # Should be str
        }

        with pytest.raises(ValidationError) as exc_info:
            TokenPayload(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("type",)
        assert errors[0]["type"] == "string_type"
