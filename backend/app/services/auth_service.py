"""
Auth Service
============
Service for authentication logic.
Refactored to maintain event-loop responsiveness and clean DI.
"""

import logging
from datetime import timedelta
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import FunctionalError, TechnicalError
from app.core.security import (ACCESS_TOKEN_EXPIRE_MINUTES,
                               create_access_token, verify_password_async)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.token import Token

logger = logging.getLogger(__name__)

# Constants
ERROR_INVALID_CREDS = "INVALID_CREDENTIALS"
ERROR_INACTIVE_USER = "USER_INACTIVE"
ERROR_AUTH_SYSTEM = "AUTH_SYSTEM_ERROR"
TOKEN_TYPE_BEARER = "bearer"


class AuthService:
    """
    Service for authentication logic.

    Responsibilities (SRP):
    1. User Retrieval (Delegated).
    2. Credentials Verification (Async Safe).
    3. Status Validation.
    4. Token Factory.
    """

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate(self, username: str, password: str) -> Token:
        """Authenticates a user and returns an access token."""
        try:
            # 1. Fetch User
            user = await self.user_repo.get_by_email(username)

            # 2. Verify Credentials & Status
            await self._verify_user_credentials(user, password, username)

            # 3. Generate Token
            token = self._create_user_token(user)

            logger.info("✅ User authenticated")
            return token

        except Exception as e:
            if isinstance(e, FunctionalError):
                raise
            logger.error(f"🚨 Unexpected Authentication Critical Error: {str(e)}", exc_info=True)
            raise TechnicalError("Authentication service temporarily unavailable", error_code=ERROR_AUTH_SYSTEM)

    # --- Private Helpers: SRP ---

    async def _verify_user_credentials(self, user: Optional[User], password: str, username: str):
        """Checks password validity and user status."""
        # P0: Verify password async to avoid blocking event loop
        is_valid = False
        if user:
            is_valid = await verify_password_async(password, user.hashed_password)

        if not user or not is_valid:
            logger.warning(f"⛔ Auth failed for user: {username}")
            raise FunctionalError(
                message="Incorrect email or password", error_code=ERROR_INVALID_CREDS, status_code=400
            )

        if not user.is_active:
            logger.warning(f"⛔ Inactive user login attempt: {username}")
            raise FunctionalError(message="Inactive user", error_code=ERROR_INACTIVE_USER, status_code=400)

    def _create_user_token(self, user: User) -> Token:
        """Fabrics the JWT token."""
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_str = create_access_token(subject=user.email, expires_delta=access_token_expires)
        return Token(access_token=token_str, token_type=TOKEN_TYPE_BEARER)


# --- Dependency Injection Layer ---


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthService:
    """Dependency provider for AuthService."""
    user_repo = UserRepository(db)
    return AuthService(user_repo)
