"""
Tests for User Schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserRole, UserUpdate


def test_user_create_valid():
    u = UserCreate(email="test@example.com", password="securepassword", role=UserRole.ADMIN)
    assert u.email == "test@example.com"
    assert u.role == UserRole.ADMIN
    assert u.is_active is True


def test_user_create_invalid_email():
    with pytest.raises(ValidationError) as exc:
        UserCreate(email="not-an-email", password="securepassword")
    assert "value is not a valid email address" in str(exc.value)


def test_user_create_short_password():
    with pytest.raises(ValidationError) as exc:
        UserCreate(email="test@example.com", password="123")
    assert "should have at least 8 characters" in str(exc.value)


def test_user_create_invalid_role():
    with pytest.raises(ValidationError) as exc:
        UserCreate(email="test@example.com", password="securepassword", role="superadmin")  # Invalid
    assert "Input should be 'admin' or 'user'" in str(exc.value)


def test_user_update_partial():
    u = UserUpdate(email="new@example.com")
    assert u.email == "new@example.com"
    assert u.password is None
