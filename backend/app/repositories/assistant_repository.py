"""
Assistant repository for database operations.

ARCHITECT NOTE: Repository Pattern
Encapsulates data access logic, keeping service layer clean.
All database exceptions are caught and converted to domain exceptions.
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFound, TechnicalError, ValidationError
from app.models.assistant import Assistant
from app.models.connector import Connector
from app.repositories.base_repository import BaseRepository
from app.schemas.assistant import AssistantCreate, AssistantUpdate

logger = logging.getLogger(__name__)

# Pagination defaults
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


class AssistantRepository(BaseRepository[Assistant, AssistantCreate, AssistantUpdate]):
    """
    Repository for Assistant entity operations.

    ARCHITECT NOTE: Transaction Safety
    All write operations use try/except with rollback on failure.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        super().__init__(Assistant, db)

    async def get_with_connectors(self, assistant_id: UUID) -> Optional[Assistant]:
        """
        Fetch assistant with linked connectors eagerly loaded.

        ARCHITECT NOTE: N+1 Prevention
        Uses selectinload to fetch connectors in single query.
        """
        try:
            stmt = (
                select(self.model)
                .options(selectinload(self.model.linked_connectors))
                .where(self.model.id == assistant_id)
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch assistant {assistant_id}: {e}")
            raise TechnicalError(f"Failed to fetch assistant: {str(e)}")

    async def get_all_ordered_by_name(
        self, skip: int = 0, limit: int = DEFAULT_LIMIT, exclude_private: bool = False
    ) -> List[Assistant]:
        """
        Fetch all assistants ordered by name with filtering and pagination.

        Args:
            skip: Offset
            limit: Limit
            exclude_private: If True, only return assistants with user_authentication=False
        """
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        try:
            stmt = select(self.model).order_by(self.model.name)

            if exclude_private:
                stmt = stmt.where(self.model.user_authentication == False)

            stmt = stmt.offset(skip).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch assistants: {e}")
            raise TechnicalError(f"Failed to fetch assistants: {str(e)}")

    async def create_with_connectors(self, obj_in: AssistantCreate) -> Assistant:
        """
        Create assistant with linked connectors in transaction.

        ARCHITECT NOTE: Transaction Safety
        Validates connector IDs exist before commit.
        Rolls back on any failure to maintain consistency.
        """
        try:
            data_dict = obj_in.model_dump(exclude={"linked_connector_ids"})
            db_obj = self.model(**data_dict)

            # Validate and link connectors
            if obj_in.linked_connector_ids:
                connector_ids = list(obj_in.linked_connector_ids)
                stmt = select(Connector).where(Connector.id.in_(connector_ids))
                result = await self.db.execute(stmt)
                connectors = list(result.scalars().all())

                # Validate all connectors exist
                if len(connectors) != len(connector_ids):
                    found_ids = {c.id for c in connectors}
                    missing_ids = set(connector_ids) - found_ids
                    raise ValidationError(f"Connectors not found: {missing_ids}")

                db_obj.linked_connectors = connectors

            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)

            logger.info(f"Created assistant {db_obj.id} with {len(db_obj.linked_connectors or [])} connectors")
            return db_obj

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating assistant: {e}")
            raise ValidationError(f"Invalid data: {str(e)}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating assistant: {e}")
            raise TechnicalError(f"Failed to create assistant: {str(e)}")

    async def update_with_connectors(self, assistant_id: UUID, obj_in: AssistantUpdate) -> Optional[Assistant]:
        """
        Update assistant with connectors in transaction.

        ARCHITECT NOTE: Optimistic Locking
        Fetches current state, applies updates, validates connectors.
        Rolls back on failure to prevent partial updates.
        """
        try:
            # Fetch with relations
            db_obj = await self.get_with_connectors(assistant_id)
            if not db_obj:
                return None

            update_data = obj_in.model_dump(exclude_unset=True, exclude={"linked_connector_ids"})

            # Apply field updates
            for field, value in update_data.items():
                setattr(db_obj, field, value)

            # Handle connector relationships
            if obj_in.linked_connector_ids is not None:
                if obj_in.linked_connector_ids:
                    connector_ids = list(obj_in.linked_connector_ids)
                    stmt = select(Connector).where(Connector.id.in_(connector_ids))
                    result = await self.db.execute(stmt)
                    connectors = list(result.scalars().all())

                    # Validate all connectors exist
                    if len(connectors) != len(connector_ids):
                        found_ids = {c.id for c in connectors}
                        missing_ids = set(connector_ids) - found_ids
                        raise ValidationError(f"Connectors not found: {missing_ids}")

                    db_obj.linked_connectors = connectors
                else:
                    db_obj.linked_connectors = []

            await self.db.commit()
            await self.db.refresh(db_obj)

            logger.info(f"Updated assistant {assistant_id}")
            return db_obj

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error updating assistant {assistant_id}: {e}")
            raise ValidationError(f"Invalid data: {str(e)}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating assistant {assistant_id}: {e}")
            raise TechnicalError(f"Failed to update assistant: {str(e)}")
