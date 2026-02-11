import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.auth_service import AuthService
from app.core.exceptions import FunctionalError
from app.models.user import User
from app.schemas.token import Token

# --- Fixtures ---

@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def auth_service(mock_user_repo):
    return AuthService(user_repo=mock_user_repo)

@pytest.fixture
def sample_user():
    return User(
        id=1,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        role="user"
    )

# --- Tests ---

@pytest.mark.asyncio
async def test_authenticate_success(auth_service, mock_user_repo, sample_user):
    """Happy path: successful authentication."""
    # Arrange
    mock_user_repo.get_by_email.return_value = sample_user
    
    with patch("app.services.auth_service.verify_password_async", return_value=True), \
         patch("app.services.auth_service.create_access_token", return_value="mock_token"):
        
        # Act
        result = await auth_service.authenticate("test@example.com", "any_password")
        
        # Assert
        assert isinstance(result, Token)
        assert result.access_token == "mock_token"
        assert result.token_type == "bearer"
        mock_user_repo.get_by_email.assert_awaited_once_with("test@example.com")


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials(auth_service, mock_user_repo, sample_user):
    """Worst case: authentication fails with incorrect password."""
    # Arrange
    mock_user_repo.get_by_email.return_value = sample_user
    
    with patch("app.services.auth_service.verify_password_async", return_value=False):
        # Act & Assert
        with pytest.raises(FunctionalError) as exc:
            await auth_service.authenticate("test@example.com", "wrong_password")
        
        assert exc.value.error_code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_authenticate_inactive_user(auth_service, mock_user_repo, sample_user):
    """Worst case: authentication fails for inactive user."""
    # Arrange
    sample_user.is_active = False
    mock_user_repo.get_by_email.return_value = sample_user
    
    with patch("app.services.auth_service.verify_password_async", return_value=True):
        # Act & Assert
        with pytest.raises(FunctionalError) as exc:
            await auth_service.authenticate("test@example.com", "any_password")
        
        assert exc.value.error_code == "USER_INACTIVE"
