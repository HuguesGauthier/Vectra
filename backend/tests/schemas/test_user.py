import pytest
from uuid import uuid4
from app.schemas.user import UserBase, UserCreate, UserUpdate, UserRead, UserRole


def test_user_base_defaults():
    """Test UserBase default values."""
    user = UserBase(email="test@example.com")
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.avatar_vertical_position == 50
    assert user.first_name is None
    assert user.last_name is None
    assert user.avatar_url is None


def test_user_base_custom_values():
    """Test UserBase with custom values."""
    user = UserBase(
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=False,
        first_name="John",
        last_name="Doe",
        avatar_url="https://example.com/avatar.jpg",
        avatar_vertical_position=75,
    )
    assert user.email == "admin@example.com"
    assert user.role == UserRole.ADMIN
    assert user.is_active is False
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.avatar_url == "https://example.com/avatar.jpg"
    assert user.avatar_vertical_position == 75


def test_user_create_password_validation():
    """Test UserCreate password minimum length validation."""
    # Valid password (8+ chars)
    user = UserCreate(email="test@example.com", password="password123")
    assert user.password == "password123"

    # Too short password should fail
    with pytest.raises(ValueError):
        UserCreate(email="test@example.com", password="short")


def test_user_create_email_validation():
    """Test email validation."""
    # Valid email
    user = UserCreate(email="valid@example.com", password="password123")
    assert user.email == "valid@example.com"

    # Invalid email should fail
    with pytest.raises(ValueError):
        UserCreate(email="invalid-email", password="password123")


def test_user_avatar_position_range():
    """Test avatar_vertical_position range validation (0-100)."""
    # Valid range
    user = UserBase(email="test@example.com", avatar_vertical_position=0)
    assert user.avatar_vertical_position == 0

    user2 = UserBase(email="test@example.com", avatar_vertical_position=100)
    assert user2.avatar_vertical_position == 100

    # Out of range should fail
    with pytest.raises(ValueError):
        UserBase(email="test@example.com", avatar_vertical_position=101)

    with pytest.raises(ValueError):
        UserBase(email="test@example.com", avatar_vertical_position=-1)


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
    with pytest.raises(ValueError):
        UserUpdate(password="short")


def test_user_read_structure():
    """Test UserRead has all required fields."""
    user = UserRead(id=uuid4(), email="test@example.com")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER
    assert user.is_active is True
