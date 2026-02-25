import pytest
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.models.enums import UserRole


def test_user_create_password_validation():
    """Test UserCreate password minimum length validation."""
    # Valid password (8+ chars)
    user = UserCreate(email="test@example.com", password="password123")
    assert user.password == "password123"

    # Too short password should fail
    with pytest.raises(ValidationError):
        UserCreate(email="test@example.com", password="short")


def test_user_create_email_validation():
    """Test email validation."""
    # Valid email
    user = UserCreate(email="valid@example.com", password="password123")
    assert user.email == "valid@example.com"

    # Invalid email should fail
    with pytest.raises(ValidationError):
        UserCreate(email="invalid-email", password="password123")


def test_user_update_partial():
    """Test partial updates with UserUpdate."""
    update = UserUpdate(first_name="Jane", is_active=False)
    assert update.first_name == "Jane"
    assert update.is_active is False
    assert update.email is None
    assert update.password is None


def test_user_update_password_validation():
    """Test password validation in UserUpdate."""
    # Valid password
    update = UserUpdate(password="newpassword123")
    assert update.password == "newpassword123"

    # Too short password should fail
    with pytest.raises(ValidationError):
        UserUpdate(password="short")


def test_user_read_structure():
    """Test UserRead has all required fields."""
    user = UserRead(id=uuid4(), email="test@example.com")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER
    assert user.is_active is True
