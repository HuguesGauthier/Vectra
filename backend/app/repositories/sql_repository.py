"""
SQL Repository - Generic SQLAlchemy repository implementation.

Provides concrete implementation of BaseRepository for SQLAlchemy models.
Handles common database operations with proper error handling and session management.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from app.core.exceptions import TechnicalError
from app.repositories.base_repository import DEFAULT_LIMIT, MAX_LIMIT, BaseRepository

logger = logging.getLogger(__name__)

# Generic type constrained to SQLModel
ModelType = TypeVar("ModelType", bound=SQLModel)

# Generic schema types
CreateSchemaType = TypeVar("CreateSchemaType", bound=Union[SQLModel, Dict[str, Any]])
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=Union[SQLModel, Dict[str, Any]])


class SQLRepository(
    BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType],
    Generic[ModelType, CreateSchemaType, UpdateSchemaType],
):
    """
    Generic SQLAlchemy repository implementation.

    ARCHITECT NOTE: Generic Repository Pattern
    Provides reusable CRUD operations. Enforces strict type safety and error wrapping.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    def _apply_limit(self, limit: int) -> int:
        """Internal helper to cap limit for DoS protection."""
        if limit > MAX_LIMIT:
            return MAX_LIMIT
        return limit

    def _extract_data(self, data: Union[SQLModel, Dict[str, Any]]) -> Dict[str, Any]:
        """Extract dict data from Pydantic model or Dict."""
        if isinstance(data, dict):
            return data
        return data.model_dump(exclude_unset=True)

    async def create(self, data: CreateSchemaType) -> ModelType:
        """Create a new entity."""
        try:
            clean_data = self._extract_data(data)
            entity = self.model(**clean_data)
            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)

            pk = getattr(entity, "id", getattr(entity, "key", "unknown"))
            logger.debug(f"Created {self.model.__name__} with ID: {pk}")
            return entity

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise TechnicalError(f"Database error creating entity: {e}")

    async def create_batch(self, data_list: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple entities in a single batch without commit."""
        try:
            entities = []
            for data in data_list:
                clean_data = self._extract_data(data)
                entity = self.model(**clean_data)
                self.db.add(entity)
                entities.append(entity)

            await self.db.flush()  # Ensure IDs are populated if possible
            return entities
        except SQLAlchemyError as e:
            logger.error(f"Failed batch creation for {self.model.__name__}: {e}")
            raise TechnicalError(f"Database error during batch creation: {e}")

    async def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """Retrieve entity by ID."""
        try:
            result = await self.db.execute(select(self.model).where(self.model.id == entity_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self.model.__name__} {entity_id}: {e}")
            raise TechnicalError(f"Database error retrieving entity: {e}")

    async def get_by_ids(self, entity_ids: List[UUID]) -> List[ModelType]:
        """Retrieve multiple entities by their IDs in a single batch."""
        if not entity_ids:
            return []
        try:
            statement = select(self.model).where(self.model.id.in_(entity_ids))
            result = await self.db.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self.model.__name__} batch: {e}")
            raise TechnicalError(f"Database error retrieving entities: {e}")

    async def get_all(
        self, skip: int = 0, limit: int = DEFAULT_LIMIT, filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Retrieve all entities with pagination and filtering."""
        limit = self._apply_limit(limit)
        try:
            statement = select(self.model)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        statement = statement.where(getattr(self.model, key) == value)

            statement = statement.offset(skip).limit(limit)
            result = await self.db.execute(statement)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Failed to list {self.model.__name__}: {e}")
            raise TechnicalError(f"Database error listing entities: {e}")

    async def update(self, entity_id: UUID, data: UpdateSchemaType) -> Optional[ModelType]:
        """Update entity with partial data."""
        try:
            entity = await self.get_by_id(entity_id)
            if not entity:
                return None

            update_data = self._extract_data(data)
            for key, value in update_data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)
            return entity

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to update {self.model.__name__} {entity_id}: {e}")
            raise TechnicalError(f"Database error updating entity: {e}")

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID."""
        try:
            # Determine primary key (id or key)
            if hasattr(self.model, "id"):
                statement = sql_delete(self.model).where(self.model.id == entity_id)
            elif hasattr(self.model, "key"):
                # Assuming entity_id is actually the key in this case, or this method is misused for Setting
                # But SettingRepository overrides delete/update usually?
                # SettingRepository does NOT override delete, so this might fail if we try to delete a setting by UUID using this generic method.
                # However, generic repo expects UUID usually.
                # For the specific crash, it was in CREATE.
                # Let's fix the crash first.
                statement = sql_delete(self.model).where(self.model.key == entity_id)
            else:
                raise TechnicalError(f"Model {self.model.__name__} has no known primary key")
            result = await self.db.execute(statement)
            deleted = result.rowcount > 0

            await self.db.commit()

            if deleted:
                logger.debug(f"Deleted {self.model.__name__} {entity_id}")
            return deleted

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to delete {self.model.__name__} {entity_id}: {e}")
            raise TechnicalError(f"Database error deleting entity: {e}")

    async def delete_batch(self, entity_ids: List[UUID]) -> int:
        """Delete multiple entities by ID in a single batch without commit."""
        try:
            statement = sql_delete(self.model).where(self.model.id.in_(entity_ids))
            result = await self.db.execute(statement)
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Failed batch deletion for {self.model.__name__}: {e}")
            raise TechnicalError(f"Database error during batch deletion: {e}")

    async def update_batch(self, update_tasks: List[Dict[str, Any]]) -> int:
        """
        Processes a list of updates without individual commits.

        WARNING: Does NOT commit. Caller must ensure transaction management.

        update_tasks: List of dicts, each must contain 'id' and the fields to update.
        """
        try:
            count = 0
            for task in update_tasks:
                # Avoid mutating input dict
                entity_id = task.get("id")
                if not entity_id:
                    continue

                entity = await self.get_by_id(entity_id)
                if entity:
                    for key, value in task.items():
                        if key != "id" and hasattr(entity, key):
                            setattr(entity, key, value)
                    self.db.add(entity)
                    count += 1

            await self.db.flush()
            return count
        except SQLAlchemyError as e:
            logger.error(f"Failed batch update for {self.model.__name__}: {e}")
            raise TechnicalError(f"Database error during batch update: {e}")

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching filters."""
        try:
            statement = select(func.count()).select_from(self.model)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        statement = statement.where(getattr(self.model, key) == value)

            result = await self.db.execute(statement)
            return result.scalar_one()
        except SQLAlchemyError as e:
            logger.error(f"Failed to count {self.model.__name__}: {e}")
            raise TechnicalError(f"Database error counting entities: {e}")

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        try:
            statement = select(func.count()).select_from(self.model).where(self.model.id == entity_id)
            result = await self.db.execute(statement)
            return result.scalar_one() > 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to check existence {entity_id}: {e}")
            raise TechnicalError(f"Database error checking existence: {e}")
