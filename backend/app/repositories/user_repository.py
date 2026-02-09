"""
User Repository - Manages User entity data access.

Extends SQLRepository with user-specific queries and operations.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TechnicalError
from app.models.user import User
from app.repositories.sql_repository import SQLRepository
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserRepository(SQLRepository[User, UserCreate, UserUpdate]):
    """
    User-specific repository.

    ARCHITECT NOTE: Single Responsibility
    Encapsulates all user data access logic in one place.
    Services don't need to know SQL - they just call repository methods.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address.

        Args:
            email: User's email address

        Returns:
            User instance or None if not found

        Raises:
            TechnicalError: Database query failed
        """
        try:
            statement = select(User).where(User.email == email)
            result = await self.db.execute(statement)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise TechnicalError(f"Database error fetching user: {e}")

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieve all active users."""
        limit = self._apply_limit(limit)
        return await self.get_all(skip=skip, limit=limit, filters={"is_active": True})

    async def get_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieve users by role."""
        limit = self._apply_limit(limit)
        return await self.get_all(skip=skip, limit=limit, filters={"role": role})

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Soft delete: Set user as inactive instead of deleting."""
        # Ideally, we pass UserUpdate(is_active=False)
        return await self.update(user_id, UserUpdate(is_active=False))

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """Reactivate a previously deactivated user."""
        return await self.update(user_id, UserUpdate(is_active=True))

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        user = await self.get_by_email(email)
        return user is not None
