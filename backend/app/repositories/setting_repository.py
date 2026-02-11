"""
Setting Repository.
"""

import logging
from typing import Dict, List, Optional, Set

from sqlalchemy import and_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.setting import Setting
from app.repositories.sql_repository import SQLRepository
from app.schemas.setting import SettingCreate, SettingUpdate

logger = logging.getLogger(__name__)


class SettingRepository(SQLRepository[Setting, SettingCreate, SettingUpdate]):
    """
    Repository for managing Application Settings.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Setting, db)

    async def get_by_key(self, key: str) -> Optional[Setting]:
        """Fetch a single setting by its unique key."""
        try:
            result = await self.db.execute(select(Setting).where(Setting.key == key))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch setting {key}: {e}")
            raise TechnicalError(f"Database error fetching setting: {e}")

    async def get_all_keys(self) -> Set[str]:
        """Retrieve all setting keys."""
        try:
            result = await self.db.execute(select(Setting.key))
            return set(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch all setting keys: {e}")
            raise TechnicalError(f"Database error fetching keys: {e}")

    async def get_by_group(self, group: str) -> List[Setting]:
        """Fetch all settings belonging to a specific group."""
        try:
            stmt = select(Setting).where(Setting.group == group).order_by(Setting.key)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch settings for group {group}: {e}")
            raise TechnicalError(f"Database error fetching group: {e}")

    async def update_by_key(self, key: str, data: Dict[str, str]) -> Optional[Setting]:
        """Update a setting by its key."""
        try:
            # Check existence first or just update
            setting = await self.get_by_key(key)
            if not setting:
                return None

            # Secure update: Only 'value' is mutable via this method.
            # 'key' and 'group' are structural identifiers.
            if "value" in data:
                setting.value = data["value"]

            self.db.add(setting)
            await self.db.commit()
            await self.db.refresh(setting)
            return setting

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to update setting {key}: {e}")
            raise TechnicalError(f"Database error updating setting: {e}")

    async def update_bulk(self, updates: Dict[str, str]) -> int:
        """
        Atomically update multiple settings.

        Args:
            updates: Dictionary mapping setting keys to new values.

        Returns:
            Number of settings updated.
        """
        if not updates:
            return 0

        try:
            updated_count = 0
            # We iterate to allow potential future validation logic per key if needed,
            # but for raw speed/atomicity we could use a CASE statement.
            # Given the low volume of settings, a loop within a single transaction is fine
            # and safer for ensuring consistency/listeners if we add them later.
            for key, value in updates.items():
                stmt = update(Setting).where(Setting.key == key).values(value=value)
                result = await self.db.execute(stmt)
                updated_count += result.rowcount

            await self.db.commit()
            logger.info(f"Bulk updated {updated_count} settings")
            return updated_count

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk update settings: {e}")
            raise TechnicalError(f"Bulk update failed: {e}")
