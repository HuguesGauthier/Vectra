"""
Settings API endpoints.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends

from app.core.exceptions import TechnicalError
from app.core.security import get_current_admin, get_current_user
from app.models.setting import Setting
from app.models.user import User
from app.schemas.setting import SettingUpdate
from app.services.settings_service import SettingsService, get_settings_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[Setting])
async def get_settings(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Setting]:
    """
    List all settings with secrets masked.

    This endpoint ensures default settings exist (self-healing) and returns all
    settings. Secrets are masked with asterisks for security.
    Logged in users only.

    Args:
        service: The settings service instance.
        current_user: The currently authenticated user.

    Returns:
        A list of settings with masked secret values.

    Raises:
        TechnicalError: If there is an error fetching the settings.
    """
    try:
        # Self-healing: ensure defaults exist
        await service.seed_defaults()

        settings = await service.get_all_settings()

        # Mask secrets for display
        for s in settings:
            if s.is_secret:
                s.value = "********"

        return settings

    except Exception as e:
        logger.error(f"❌ FAIL | get_settings | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to fetch settings: {e}") from e


@router.put("/", response_model=List[Setting])
async def update_settings(
    settings_in: List[SettingUpdate],
    service: Annotated[SettingsService, Depends(get_settings_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> List[Setting]:
    """
    Batch update settings.

    This endpoint allows administrators to update multiple settings at once.
    Secrets in the response are masked.

    Args:
        settings_in: A list of settings to update.
        service: The settings service instance.
        current_admin: The currently authenticated administrator.

    Returns:
        A list of the updated settings with masked secret values.

    Raises:
        TechnicalError: If there is an error updating the settings.
    """
    try:
        updated_settings = []

        # Note: Ideally a bulk update transactional service method would be better
        # but for settings (low volume), simple loop is acceptable for now.
        for s in settings_in:
            upd = await service.update_setting(key=s.key, value=s.value, group=s.group, is_secret=s.is_secret)
            updated_settings.append(upd)

        # Mask secrets in response
        for s in updated_settings:
            if s.is_secret:
                s.value = "********"

        return updated_settings

    except Exception as e:
        logger.error(f"❌ FAIL | update_settings | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to update settings: {e}") from e
