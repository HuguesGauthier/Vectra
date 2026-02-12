"""
Unit tests for User model.
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError
from app.models.user import User, UserRole


class TestUserModel:
    """Test User model."""

    def test_user_creation_valid(self):
        """Valid user should be created."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_content",
            role=UserRole.USER,
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.avatar_vertical_position == 50

    def test_user_defaults(self):
        """Default values should be set correctly."""
        user = User(email="test@example.com", hashed_password="...")
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.avatar_vertical_position == 50

    def test_user_custom_values(self):
        """User with custom values should work."""
        user = User(
            email="admin@example.com",
            hashed_password="...",
            role=UserRole.ADMIN,
            is_active=False,
            first_name="John",
            last_name="Doe",
            avatar_vertical_position=75,
        )
        assert user.role == UserRole.ADMIN
        assert user.is_active is False
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.avatar_vertical_position == 75

    def test_validation_on_assignment(self):
        """Validation should trigger on attribute assignment (Robustness P1)."""
        user = User(email="test@example.com", hashed_password="...")

        # Test range validation (ge=0, le=100)
        with pytest.raises(ValidationError):
            user.avatar_vertical_position = 101

        with pytest.raises(ValidationError):
            user.avatar_vertical_position = -1

    def test_email_validation_on_assignment(self):
        """Email validation should trigger on assignment (Robustness P1)."""
        user = User(email="valid@example.com", hashed_password="...")

        with pytest.raises(ValidationError):
            user.email = "not-an-email"
