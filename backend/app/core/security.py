import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional, Union

import bcrypt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

# Hack for passlib 1.7.4 compatibility with bcrypt 4.0+
if not hasattr(bcrypt, "__about__"):
    try:
        from dataclasses import dataclass

        @dataclass
        class About:
            __version__: str

        bcrypt.__about__ = About(__version__=bcrypt.__version__)
    except Exception:
        pass  # Best effort


from app.core.database import get_db
from app.core.exceptions import FunctionalError, TechnicalError, UnauthorizedAction
from app.core.settings import settings
from app.models.user import User

# Logger
logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 1 month

# Bcrypt 4.0+ breaks passlib 1.7.4. Switching to pbkdf2_sha256 (NIST approved) for stability.

pwd_context = CryptContext(schemes=["pbkdf2_sha256"])
# DEBUG: auto_error=False to debug why token is not seen
oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a raw password against a hash (Blocking)."""
    return pwd_context.verify(plain_password, hashed_password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a raw password against a hash (Non-Blocking).
    Offloads CPU-intensive PBKDF2 calculation to a thread.
    """
    return await run_in_threadpool(verify_password, plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a password (Blocking)."""
    return pwd_context.hash(password)


async def get_password_hash_async(password: str) -> str:
    """
    Hashes a password (Non-Blocking).
    Offloads CPU-intensive PBKDF2 calculation to a thread.
    """
    return await run_in_threadpool(get_password_hash, password)


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    start_time = time.time()
    func_name = "create_access_token"

    try:
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {"exp": expire, "sub": str(subject)}
        # JWT encoding is fast enough for HS256 to stay sync
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.debug(f"FINISH | {func_name} | Status: Success | Duration: {elapsed}ms")

        return encoded_jwt
    except Exception as e:
        logger.error(f"❌ FAIL | {func_name} | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to create access token: {e}")


async def _get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Internal helper to resolve user from token.
    Sharing session ensures transaction consistency.
    """
    try:
        # P1: Avoid logging partial tokens/secrets even at INFO level
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: Optional[str] = payload.get("sub")
            logger.debug(f"🔑 AUTH | Decoded Subject: {email}")

            if email is None:
                logger.warning("❌ AUTH FAIL | Subject missing in token")
                raise UnauthorizedAction("Invalid token: Subject missing")
        except JWTError as e:
            logger.warning(f"❌ AUTH FAIL | JWT Decode Error: {e}")
            raise UnauthorizedAction(f"Could not validate credentials: {e}")

        try:
            # Query DB using injected session
            statement = select(User).where(User.email == email)
            result = await db.execute(statement)
            user = result.scalar_one_or_none()
        except Exception as e:
            raise TechnicalError(f"Database error during user retrieval: {e}")

        if user is None:
            logger.warning(f"❌ AUTH FAIL | User not found in DB: {email}")
            raise UnauthorizedAction("User not found")

        if not user.is_active:
            logger.warning(f"❌ AUTH FAIL | Inactive user: {email}")
            raise UnauthorizedAction("Inactive user")

        logger.debug(f"✅ AUTH SUCCESS | User: {user.email}")
        return user

    except (UnauthorizedAction, TechnicalError):
        logger.warning("❌ AUTH FAIL | Known/Business Error")
        raise
    except Exception as e:
        logger.error(f"❌ AUTH FAIL | Unexpected: {e}", exc_info=True)
        raise TechnicalError("Authentication failed")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_schema)], db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency that retrieves the current authenticated user.
    """
    return await _get_user_from_token(token, db)


async def get_current_admin(
    token: Annotated[str, Depends(oauth2_schema)], db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency that retrieves the current authenticated admin user.
    """
    user = await _get_user_from_token(token, db)

    if user.role != "admin":
        logger.warning(f"❌ AUTH FAIL | Admin privilege required. User: {user.email}")
        raise FunctionalError(
            message="The user does not have enough privileges",
            error_code="INSUFFICIENT_PRIVILEGES",
            status_code=403,
            details={"user_role": user.role},
        )
    return user


# Optional Auth
oauth2_schema_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_schema_optional)], db: Annotated[AsyncSession, Depends(get_db)]
) -> Optional[User]:
    """
    Dependency that retrieves the current authenticated user if present, otherwise returns None.
    Does not raise 401.
    """
    if not token:
        return None

    try:
        return await _get_user_from_token(token, db)
    except (UnauthorizedAction, FunctionalError, TechnicalError):
        return None
    except Exception:
        return None
