"""
Settings API endpoints.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends

from app.core.exceptions import TechnicalError
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.setting import SettingResponse, SettingUpdate
from app.services.settings_service import SettingsService, get_settings_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _mask_secrets(settings: list) -> list:
    """Helper to mask secret values for API response."""
    for s in settings:
        if s.is_secret:
            s.value = "********"
    return settings


@router.get("/", response_model=List[SettingResponse])
async def get_settings(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[SettingResponse]:
    """
    List all settings with secrets masked.

    This endpoint ensures default settings exist (self-healing) and returns all
    settings. Secrets are masked with asterisks for security.
    Logged in users only.

    Args:
        service: The settings service instance.
        current_user: The currently authenticated user.

    Returns:
        List[SettingResponse]: A list of settings with masked secret values.

    Raises:
        TechnicalError: If there is an error fetching the settings.
    """
    try:
        # Self-healing: ensure defaults exist
        await service.seed_defaults()

        settings = await service.get_all_settings()

        # Mask secrets for display
        return _mask_secrets(settings)

    except Exception as e:
        logger.error(f"❌ FAIL | get_settings | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to fetch settings: {e}") from e


@router.put("/", response_model=List[SettingResponse])
async def update_settings(
    settings_in: List[SettingUpdate],
    service: Annotated[SettingsService, Depends(get_settings_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> List[SettingResponse]:
    """
    Batch update settings.

    This endpoint allows administrators to update multiple settings at once.
    Secrets in the response are masked.

    Args:
        settings_in: A list of settings to update.
        service: The settings service instance.
        current_admin: The currently authenticated administrator.

    Returns:
        List[SettingResponse]: A list of the updated settings with masked secret values.

    Raises:
        TechnicalError: If there is an error updating the settings.
    """
    try:
        # Convert Pydantic schemas to list of dicts for service
        updates = [s.model_dump(exclude_unset=True) for s in settings_in]

        # Transactional Batch Update
        updated_settings = await service.update_settings_batch(updates)

        # Mask secrets in response
        return _mask_secrets(updated_settings)

    except Exception as e:
        logger.error(f"❌ FAIL | update_settings | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to update settings: {e}") from e
