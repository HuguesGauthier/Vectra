import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.exceptions import FunctionalError, TechnicalError
from app.schemas.token import Token
from app.services.auth_service import AuthService, get_auth_service

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.

    Security:
    - Uses strict OAuth2 form (username/password).
    - Rate Limiting should be applied at Gateway/Nginx level or via Middleware.

    Args:
        form_data: OAuth2 password request form containing username and password.
        auth_service: Injected authentication service.

    Returns:
        Token: A Token object containing the access token and token type.

    Raises:
        FunctionalError: If authentication fails due to invalid credentials or inactive user.
        TechnicalError: If an unexpected error occurs during authentication.
    """
    try:
        # P1 Fix: Use injected service, no direct DB access here
        return await auth_service.authenticate(form_data.username, form_data.password)

    except (FunctionalError, TechnicalError):
        # Re-raise known exceptions to be handled by global exception handlers
        raise
    except Exception as e:
        # P2 Fix: Clean logging handled in Exception Handler ideally, but keeping context here
        logger.error(f"Login failed unexpectedly: {e}", exc_info=True)
        raise TechnicalError("Login failed")
