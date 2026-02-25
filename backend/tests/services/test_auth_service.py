from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.schemas.token import Token
from app.services.auth_service import (AuthService, FunctionalError,
                                       TechnicalError)


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_user_repo):
    return AuthService(mock_user_repo)


@pytest.fixture
def sample_user():
    return User(id=uuid4(), email="test@example.com", hashed_password="hashed_pwd", is_active=True)


@pytest.mark.asyncio
class TestAuthService:

    @patch("app.services.auth_service.verify_password_async")
    @patch("app.services.auth_service.create_access_token")
    async def test_authenticate_success(self, mock_create_token, mock_verify_pwd, service, mock_user_repo, sample_user):
        # Setup
        mock_user_repo.get_by_email.return_value = sample_user
        mock_verify_pwd.return_value = True
        mock_create_token.return_value = "fake_jwt_token"

        # Execute
        result = await service.authenticate("test@example.com", "password123")

        # Verify
        assert isinstance(result, Token)
        assert result.access_token == "fake_jwt_token"
        assert result.token_type == "bearer"

        mock_user_repo.get_by_email.assert_awaited_once_with("test@example.com")
        mock_verify_pwd.assert_awaited_once_with("password123", "hashed_pwd")
        mock_create_token.assert_called_once()

    @patch("app.services.auth_service.verify_password_async")
    async def test_authenticate_invalid_credentials(self, mock_verify_pwd, service, mock_user_repo, sample_user):
        # Setup: User found but wrong password
        mock_user_repo.get_by_email.return_value = sample_user
        mock_verify_pwd.return_value = False

        # Execute & Verify
        with pytest.raises(FunctionalError) as exc:
            await service.authenticate("test@example.com", "wrong_pwd")

        assert exc.value.error_code == "INVALID_CREDENTIALS"
        assert exc.value.status_code == 400

    async def test_authenticate_user_not_found(self, service, mock_user_repo):
        # Setup: User not found
        mock_user_repo.get_by_email.return_value = None

        # Execute & Verify
        with pytest.raises(FunctionalError) as exc:
            await service.authenticate("missing@example.com", "pwd")

        assert exc.value.error_code == "INVALID_CREDENTIALS"

    async def test_authenticate_inactive_user(self, service, mock_user_repo, sample_user):
        # Setup: User found but inactive
        sample_user.is_active = False
        mock_user_repo.get_by_email.return_value = sample_user

        # Note: We don't even reach password verification if user is inactive
        # (or verify before checking status - in this implementation we verify pwd first)
        # Actually in the code: pwd is verified BEFORE checking is_active.

        with patch("app.services.auth_service.verify_password_async", return_value=True):
            with pytest.raises(FunctionalError) as exc:
                await service.authenticate("test@example.com", "pwd")

            assert exc.value.error_code == "USER_INACTIVE"

    async def test_authenticate_unexpected_error(self, service, mock_user_repo):
        # Setup: Repository fails
        mock_user_repo.get_by_email.side_effect = Exception("System failure")

        # Execute & Verify
        with pytest.raises(TechnicalError) as exc:
            await service.authenticate("test@example.com", "pwd")

        assert "Authentication service temporarily unavailable" in str(exc.value)
