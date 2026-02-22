import asyncio
import logging
import shutil
from pathlib import Path
from typing import Annotated, Any, List, Optional
from uuid import UUID

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

# Avatar storage directory - Absolute path relative to backend root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
AVATAR_DIR = BASE_DIR / "user_avatars"


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserRepository(db)

    async def get_by_id(self, user_id: UUID) -> User:
        """
        Get a user by ID.
        """
        try:
            user = await self.repository.get(user_id)
            if not user:
                raise EntityNotFound(entity_type="User", entity_id=str(user_id))
            return user
        except EntityNotFound:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch user {user_id}: {e}", exc_info=True)
            raise TechnicalError(f"Database error while fetching user: {e}")

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.
        """
        return await self.repository.get_by_email(email)

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get multiple users.
        """
        try:
            return await self.repository.get_all(skip=skip, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch users: {e}", exc_info=True)
            raise TechnicalError(f"Database error while fetching users: {e}")

    async def create(self, user_in: UserCreate) -> User:
        """
        Create a new user.
        """
        # Check if user exists
        if await self.repository.email_exists(user_in.email):
            raise FunctionalError(
                message="A user with this email already exists.", error_code="USER_EXISTS", status_code=400
            )

        try:
            # Pydantic's model_dump is more robust for field mapping
            user_data = user_in.model_dump(exclude={"password"})
            user = User(
                **user_data,
                hashed_password=get_password_hash(user_in.password),
            )
            # Use repository create
            return await self.repository.create(user)
        except Exception as e:
            logger.error(f"Failed to create user {user_in.email}: {e}", exc_info=True)
            raise TechnicalError(f"Database error while creating user: {e}")

    async def update(self, user_id: UUID, user_in: UserUpdate) -> User:
        """
        Update a user.
        """
        user = await self.get_by_id(user_id)

        try:
            update_data = user_in.model_dump(exclude_unset=True)

            if "password" in update_data and update_data["password"]:
                hashed_password = get_password_hash(update_data["password"])
                del update_data["password"]
                update_data["hashed_password"] = hashed_password

            # Cleanup avatar if it's being removed
            if "avatar_url" in update_data and (update_data["avatar_url"] is None or update_data["avatar_url"] == ""):
                await self._cleanup_avatar_file(user_id)
                # Ensure we strictly set it to None in DB if it was empty string
                update_data["avatar_url"] = None

            # Use repository update
            return await self.repository.update(user_id, update_data)
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)
            raise TechnicalError(f"Database error while updating user: {e}")

    async def delete(self, user_id: UUID) -> User:
        """
        Delete a user.
        """
        # Ensure user exists first
        user = await self.get_by_id(user_id)

        try:
            # Use repository delete
            await self.repository.delete(user_id)
            return user
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
            raise TechnicalError(f"Database error while deleting user: {e}")

    async def upload_avatar(self, user_id: UUID, file: UploadFile) -> User:
        """
        Upload and save an avatar image for a user.
        Uses run_in_executor to prevent blocking the Event Loop during I/O.
        """
        try:
            # 1. Ensure avatar directory exists (Lazy initialization)
            def _ensure_dir():
                if not AVATAR_DIR.exists():
                    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _ensure_dir)

            # 2. Validate file type
            if not file.content_type or not file.content_type.startswith("image/"):
                raise FunctionalError("File must be an image")

            # Validate file size (5MB max)
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning

            if file_size > 5 * 1024 * 1024:  # 5MB
                raise FunctionalError("File size must be less than 5MB")

            # Extract extension
            extension = "png"
            if file.filename:
                parts = file.filename.split(".")
                if len(parts) > 1:
                    ext_candidate = parts[-1].lower()
                    if ext_candidate in ["png", "jpg", "jpeg", "gif", "webp"]:
                        extension = ext_candidate

            filename = f"{user_id}.{extension}"
            file_path = AVATAR_DIR / filename

            # Cleanup old avatar
            await self._cleanup_avatar_file(user_id)

            # Non-blocking write
            loop = asyncio.get_running_loop()

            def save_file_sync():
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

            await loop.run_in_executor(None, save_file_sync)

            # Update User record with avatar URL
            # URL points to the API endpoint that serves the file
            avatar_url = f"/users/{user_id}/avatar"
            update_data = {"avatar_url": avatar_url}
            updated_user = await self.repository.update(user_id, update_data)

            logger.info(f"Uploaded avatar for user {user_id}: {filename}")
            return updated_user

        except FunctionalError:
            raise
        except Exception as e:
            logger.error(f"Failed to upload avatar for {user_id}: {e}", exc_info=True)
            raise TechnicalError(f"Failed to upload avatar: {e}", error_code="AVATAR_UPLOAD_FAILED")

    async def remove_avatar(self, user_id: UUID) -> User:
        """Remove the avatar image from a user."""
        try:
            await self._cleanup_avatar_file(user_id)

            # Update DB
            update_data = {"avatar_url": None}
            updated_user = await self.repository.update(user_id, update_data)

            return updated_user
        except Exception as e:
            logger.error(f"Failed to remove avatar for {user_id}: {e}", exc_info=True)
            raise TechnicalError("Failed to remove avatar", error_code="AVATAR_REMOVAL_FAILED")

    async def _cleanup_avatar_file(self, user_id: UUID):
        """
        Helper to remove any avatar file associated with a user ID.
        Executed in thread pool to avoid blocking loop.
        """

        def _delete_sync():
            try:
                # Search for files starting with this UUID
                for f in AVATAR_DIR.glob(f"{user_id}.*"):
                    if f.is_file():
                        f.unlink(missing_ok=True)
                        logger.debug(f"Removed avatar file: {f}")
            except Exception as e:
                logger.warning(f"Failed to cleanup avatar file for {user_id}: {e}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _delete_sync)

    async def get_avatar_path(self, user_id: UUID) -> Optional[Path]:
        """Get the file path for a user's avatar."""
        user = await self.repository.get(user_id)
        if not user or not user.avatar_url:
            return None

        # P0 FIX: Offload glob to thread pool
        def _find_path():
            try:
                params = list(AVATAR_DIR.glob(f"{user_id}.*"))
                return params[0] if params else None
            except Exception:
                return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _find_path)


async def get_user_service(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    return UserService(db)
