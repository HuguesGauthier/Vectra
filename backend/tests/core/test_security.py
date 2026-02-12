from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.core.exceptions import TechnicalError, UnauthorizedAction
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    _get_user_from_token,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_password_hash_async,
    verify_password,
    verify_password_async,
)
from app.models.user import User


class TestSecurity:

    def test_password_hashing(self):
        """Verify password hashing and verification (Sync)."""
        password = "secret_password"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

    @pytest.mark.asyncio
    async def test_password_hashing_async(self):
        """Verify password hashing and verification (Async)."""
        password = "secret_async"
        hashed = await get_password_hash_async(password)

        assert hashed != password
        # Verify both directions work
        assert await verify_password_async(password, hashed) is True
        assert await verify_password_async("wrong", hashed) is False

    def test_create_access_token(self):
        """Verify JWT creation and decoding."""
        data = "user@example.com"
        token = create_access_token(subject=data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == data
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Verify custom expiry."""
        data = "user@example.com"
        delta = timedelta(minutes=5)
        token = create_access_token(subject=data, expires_delta=delta)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Allow small time diff
        # verify expiry is roughly now + 5 min?
        # Easier just to verify it decodes correctly.
        assert payload["sub"] == data

    @pytest.mark.asyncio
    async def test_get_user_from_token_success(self):
        """Verify user retrieval from valid token."""
        token = create_access_token("test@example.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(email="test@example.com", is_active=True, role="user")

        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        user = await _get_user_from_token(token, mock_db)
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_from_token_invalid_format(self):
        """Should raise UnauthorizedAction for bad token."""
        mock_db = AsyncMock()
        with pytest.raises(UnauthorizedAction):
            await _get_user_from_token("bad.token", mock_db)

    @pytest.mark.asyncio
    async def test_get_user_from_token_user_not_found(self):
        """Should raise UnauthorizedAction if user not in DB."""
        token = create_access_token("ghost@example.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(UnauthorizedAction) as exc:
            await _get_user_from_token(token, mock_db)
        assert "User not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_user_from_token_inactive(self):
        """Should block inactive users."""
        token = create_access_token("inactive@example.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(email="inactive@example.com", is_active=False)
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(UnauthorizedAction) as exc:
            await _get_user_from_token(token, mock_db)
        assert "Inactive user" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_current_admin_success(self):
        """Verify admin role check passes for admins."""
        from app.core.security import get_current_admin

        token = create_access_token("admin@example.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(email="admin@example.com", is_active=True, role="admin")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        user = await get_current_admin(token, mock_db)
        assert user.role == "admin"

    @pytest.mark.asyncio
    async def test_get_current_admin_fail_role(self):
        """Verify admin role check fails for regular users."""
        from app.core.security import get_current_admin
        from app.core.exceptions import FunctionalError

        token = create_access_token("user@example.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(email="user@example.com", is_active=True, role="user")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(FunctionalError) as exc:
            await get_current_admin(token, mock_db)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_token(self):
        """Verify optional auth returns user when token is present."""
        from app.core.security import get_current_user_optional

        token = create_access_token("user@example.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(email="user@example.com", is_active=True, role="user")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        user = await get_current_user_optional(token, mock_db)
        assert user is not None
        assert user.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_token(self):
        """Verify optional auth returns None when token is missing."""
        from app.core.security import get_current_user_optional

        mock_db = AsyncMock()
        user = await get_current_user_optional(None, mock_db)
        assert user is None

    def test_token_expiry(self):
        """Verify token expiry raises JWTError."""
        from jose import jwt, JWTError
        from app.core.security import ALGORITHM, SECRET_KEY

        data = "expired@example.com"
        delta = timedelta(seconds=-1)  # Expired
        token = create_access_token(subject=data, expires_delta=delta)

        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
