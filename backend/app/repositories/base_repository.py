"""
Base Repository Pattern - Generic repository implementation.

ARCHITECT NOTE: Repository Pattern with Type Safety
Provides concrete CRUD operations with enhanced type safety and error handling.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import TechnicalError, ValidationError

logger = logging.getLogger(__name__)

# Generic types for repository pattern
ModelType = TypeVar("ModelType", bound=Any)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# Pagination constants
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository for CRUD operations.

    ARCHITECT NOTE: Generic Repository Pattern
    Provides type-safe CRUD operations with error handling.
    Implementations can override for custom behavior.

    Type Parameters:
        ModelType: Database model class
        CreateSchemaType: Pydantic schema for creation
        UpdateSchemaType: Pydantic schema for updates
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLModel class
            db: Database session
        """
        self.model = model
        self.db = db

    async def get(self, id: Union[UUID, str]) -> Optional[ModelType]:
        """
        Retrieve entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found

        Raises:
            TechnicalError: Database query failed
        """
        try:
            result = await self.db.execute(select(self.model).where(self.model.id == id))
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching {self.model.__name__} {id}: {e}")
            raise TechnicalError(f"Failed to fetch entity: {str(e)}")

    async def get_all(self, skip: int = 0, limit: int = DEFAULT_LIMIT) -> List[ModelType]:
        """
        Retrieve all entities with pagination.

        ARCHITECT NOTE: DoS Prevention
        Limit is capped at MAX_LIMIT.

        Args:
            skip: Offset
            limit: Max records (default: 100, max: 1000)

        Returns:
            List of entities

        Raises:
            TechnicalError: Database query failed
        """
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        try:
            result = await self.db.execute(select(self.model).offset(skip).limit(limit))
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching {self.model.__name__} list: {e}")
            raise TechnicalError(f"Failed to fetch entities: {str(e)}")

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create entity.

        Args:
            obj_in: Creation schema

        Returns:
            Created entity

        Raises:
            ValidationError: Invalid data
            TechnicalError: Database error
        """
        try:
            obj_in_data = obj_in.model_dump()
            db_obj = self.model(**obj_in_data)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)

            logger.info(f"Created {self.model.__name__}")
            return db_obj

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise ValidationError(f"Invalid data: {str(e)}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise TechnicalError(f"Failed to create entity: {str(e)}")

    async def update(self, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        Update entity.

        Args:
            db_obj: Existing entity
            obj_in: Update schema or dict

        Returns:
            Updated entity

        Raises:
            ValidationError: Invalid data
            TechnicalError: Database error
        """
        try:
            obj_data = obj_in.model_dump(exclude_unset=True) if not isinstance(obj_in, dict) else obj_in

            for field in obj_data:
                if hasattr(db_obj, field):
                    setattr(db_obj, field, obj_data[field])

            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)

            logger.info(f"Updated {self.model.__name__}")
            return db_obj

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error updating {self.model.__name__}: {e}")
            raise ValidationError(f"Invalid data: {str(e)}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating {self.model.__name__}: {e}")
            raise TechnicalError(f"Failed to update entity: {str(e)}")

    async def remove(self, id: Union[UUID, str]) -> Optional[ModelType]:
        """
        Delete entity.

        Args:
            id: Entity ID

        Returns:
            Deleted entity or None

        Raises:
            TechnicalError: Database error
        """
        try:
            obj = await self.get(id)
            if obj:
                await self.db.delete(obj)
                await self.db.commit()
                logger.info(f"Deleted {self.model.__name__} {id}")
            return obj
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting {self.model.__name__} {id}: {e}")
            raise TechnicalError(f"Failed to delete entity: {str(e)}")

    async def count(self) -> int:
        """
        Count all entities.

        Returns:
            Total count

        Raises:
            TechnicalError: Database error
        """
        try:
            stmt = select(func.count()).select_from(self.model)
            result = await self.db.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError as e:
            logger.error(f"Database error counting {self.model.__name__}: {e}")
            raise TechnicalError(f"Failed to count entities: {str(e)}")

    async def exists(self, id: Union[UUID, str]) -> bool:
        """
        Check if entity exists.

        Args:
            id: Entity ID

        Returns:
            True if exists

        Raises:
            TechnicalError: Database error
        """
        try:
            stmt = select(func.count()).select_from(self.model).where(self.model.id == id)
            result = await self.db.execute(stmt)
            return result.scalar_one() > 0
        except SQLAlchemyError as e:
            logger.error(f"Database error checking {self.model.__name__} {id} existence: {e}")
            raise TechnicalError(f"Failed to check entity existence: {str(e)}")
