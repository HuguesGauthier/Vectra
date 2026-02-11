"""
Assistant Service
=================
Service responsible for managing AI Assistants and their configurations.
Uses Repository Pattern for data access and Pydantic for API consistency.
"""

import asyncio
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, List, Optional
from uuid import UUID

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import FunctionalError, TechnicalError
from app.core.utils.ui import calculate_contrast_text_color
from app.repositories.assistant_repository import AssistantRepository
from app.schemas.assistant import AssistantCreate, AssistantResponse, AssistantUpdate
from app.services.trending_service import TrendingService, get_trending_service

if TYPE_CHECKING:
    from app.services.cache_service import SemanticCacheService

logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path(__file__).resolve().parent.parent.parent
AVATAR_DIR = BASE_DIR / "assistant_avatars"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
DEFAULT_EXTENSION = ".png"
ERROR_DB = "DB_ERROR"


class AssistantService:
    """
    Service responsible for managing AI Assistants.

    Responsibilities (SRP):
    1. CRUD Operations (delegated to Repository).
    2. Styling Logic (contrast calculation).
    3. File Management (Avatar uploads - Async Safe).
    4. Cache & Cleanup Management.
    """

    def __init__(
        self,
        assistant_repo: AssistantRepository,
        cache_service: Optional["SemanticCacheService"] = None,
        trending_service: Optional[TrendingService] = None,
    ):
        self.assistant_repo = assistant_repo
        self.cache_service = cache_service
        self.trending_service = trending_service
        self._ensure_avatar_dir()

    def _ensure_avatar_dir(self):
        """Ensures avatar directory exists safely."""
        if not AVATAR_DIR.exists():
            try:
                AVATAR_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"❌ Failed to create avatar directory: {e}")

    async def get_assistants(self, exclude_private: bool = False) -> List[AssistantResponse]:
        """Fetch all assistants, mapped to response schemas."""
        try:
            assistants = await self.assistant_repo.get_all_ordered_by_name(exclude_private=exclude_private)
            return [AssistantResponse.model_validate(a, from_attributes=True) for a in assistants]
        except Exception as e:
            logger.error(f"Failed to fetch assistants: {e}", exc_info=True)
            raise TechnicalError("Failed to retrieve assistants", error_code=ERROR_DB)

    async def get_assistant(self, assistant_id: UUID) -> Optional[AssistantResponse]:
        """Fetch a single assistant by ID."""
        try:
            assistant = await self.assistant_repo.get(assistant_id)
            if not assistant:
                return None
            return AssistantResponse.model_validate(assistant, from_attributes=True)
        except Exception as e:
            logger.error(f"Failed to fetch assistant {assistant_id}: {e}", exc_info=True)
            raise TechnicalError(f"Failed to retrieve assistant", error_code=ERROR_DB)

    async def get_assistant_with_connectors(self, assistant_id: UUID) -> Optional[AssistantResponse]:
        """Fetch assistant with linked connectors."""
        try:
            assistant = await self.assistant_repo.get_with_connectors(assistant_id)
            if not assistant:
                return None
            return AssistantResponse.model_validate(assistant, from_attributes=True)
        except Exception as e:
            logger.error(f"Failed to fetch assistant {assistant_id} with connectors: {e}", exc_info=True)
            raise TechnicalError(f"Failed to retrieve assistant", error_code=ERROR_DB)

    async def get_assistant_model(self, assistant_id: UUID):
        """
        Fetch raw SQLAlchemy Assistant model (for services that need the DB model directly).
        Returns the model instance, not the Pydantic schema.
        """
        try:
            assistant = await self.assistant_repo.get_with_connectors(assistant_id)
            return assistant
        except Exception as e:
            logger.error(f"Failed to fetch assistant model {assistant_id}: {e}", exc_info=True)
            raise TechnicalError(f"Failed to retrieve assistant", error_code=ERROR_DB)

    async def create_assistant(self, assistant_data: AssistantCreate) -> AssistantResponse:
        """Create a new assistant and ensure UI contrast consistency."""
        try:
            # 1. Apply Logic (UI Contrast)
            self._apply_contrast_logic(assistant_data)

            # 2. Persist
            new_assistant = await self.assistant_repo.create_with_connectors(assistant_data)
            logger.info(f"✅ Created assistant: {new_assistant.id}")

            return AssistantResponse.model_validate(new_assistant, from_attributes=True)

        except Exception as e:
            logger.error(f"Failed to create assistant: {e}", exc_info=True)
            if isinstance(e, (TechnicalError, FunctionalError)):
                raise e
            raise TechnicalError("Failed to create assistant", error_code="ASSISTANT_CREATION_FAILED")

    async def update_assistant(
        self, assistant_id: UUID, assistant_update: AssistantUpdate
    ) -> Optional[AssistantResponse]:
        """Update an assistant and optimize UI colors if needed."""
        try:
            # 1. Apply Logic
            self._apply_contrast_logic(assistant_update)

            # 2. Persist
            updated_assistant = await self.assistant_repo.update_with_connectors(assistant_id, assistant_update)

            if not updated_assistant:
                return None

            logger.info(f"✅ Updated assistant: {assistant_id}")
            return AssistantResponse.model_validate(updated_assistant, from_attributes=True)

        except Exception as e:
            logger.error(f"Failed to update assistant {assistant_id}: {e}", exc_info=True)
            if isinstance(e, (TechnicalError, FunctionalError)):
                raise e
            raise TechnicalError(f"Failed to update assistant", error_code="ASSISTANT_UPDATE_FAILED")

    async def delete_assistant(self, assistant_id: UUID) -> bool:
        """Purge an assistant from the system (DB + Files + Cache)."""
        try:
            # 1. Cleanup side-effects first (Files, Cache, Vectors)
            await self._cleanup_resources(assistant_id)

            # 2. Remove from DB
            deleted = await self.assistant_repo.remove(assistant_id)
            if deleted:
                logger.info(f"🗑️ Deleted assistant: {assistant_id}")
            return bool(deleted)

        except Exception as e:
            logger.error(f"Failed to delete assistant {assistant_id}: {e}", exc_info=True)
            raise TechnicalError(f"Failed to delete assistant", error_code="ASSISTANT_DELETION_FAILED")

    async def clear_cache(self, assistant_id: UUID) -> int:
        """Manually purge the semantic cache for this assistant."""
        if not self.cache_service:
            logger.warning("⚠️ Cache clearing requested but CacheService not available.")
            return 0
        try:
            count = await self.cache_service.clear_assistant_cache(str(assistant_id))
            logger.info(f"🧹 Cleared {count} cache entries for assistant {assistant_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to clear cache for assistant {assistant_id}: {e}", exc_info=True)
            raise TechnicalError("Failed to clear cache", error_code="CACHE_CLEAR_FAILED")

    async def upload_avatar(self, assistant_id: UUID, file: UploadFile) -> AssistantResponse:
        """Upload and save an avatar image for an assistant (Async Safe)."""
        try:
            # 1. Validate
            self._validate_image_file(file)

            # 2. Prepare Path
            extension = self._get_safe_extension(file.filename)
            filename = f"{assistant_id}{extension}"
            file_path = AVATAR_DIR / filename

            # 3. Cleanup Old & Save New (Blocking IO offloaded)
            await self._cleanup_avatar_file(assistant_id)
            await self._save_file_async(file, file_path)

            # 4. Update DB
            update_data = AssistantUpdate(avatar_image=filename)
            updated_assistant = await self.assistant_repo.update_with_connectors(assistant_id, update_data)

            logger.info(f"🖼️ Uploaded avatar for assistant {assistant_id}: {filename}")
            return AssistantResponse.model_validate(updated_assistant, from_attributes=True)

        except FunctionalError:
            raise
        except Exception as e:
            logger.error(f"Failed to upload avatar for {assistant_id}: {e}", exc_info=True)
            raise TechnicalError(f"Failed to upload avatar: {e}", error_code="AVATAR_UPLOAD_FAILED")

    async def remove_avatar(self, assistant_id: UUID) -> AssistantResponse:
        """Remove the avatar image from an assistant."""
        try:
            await self._cleanup_avatar_file(assistant_id)

            # Update DB
            update_data = AssistantUpdate(avatar_image=None)
            updated_assistant = await self.assistant_repo.update_with_connectors(assistant_id, update_data)

            return AssistantResponse.model_validate(updated_assistant, from_attributes=True)
        except Exception as e:
            logger.error(f"Failed to remove avatar for {assistant_id}: {e}", exc_info=True)
            raise TechnicalError("Failed to remove avatar", error_code="AVATAR_REMOVAL_FAILED")

    async def get_avatar_path(self, assistant_id: UUID) -> Optional[Path]:
        """Get the file path for an assistant's avatar."""
        assistant = await self.assistant_repo.get(assistant_id)
        if not assistant or not assistant.avatar_image:
            return None

        file_path = AVATAR_DIR / assistant.avatar_image
        if file_path.exists():
            return file_path
        return None

    # --- Private Helpers: SRP ---

    async def _cleanup_resources(self, assistant_id: UUID):
        """Orchestrates cleanup of all external resources (Best Effort)."""
        # 1. Avatar (Async background, already safe)
        await self._cleanup_avatar_file(assistant_id)

        # 2. Cache (Soft Fail)
        if self.cache_service:
            try:
                await self.clear_cache(assistant_id)
            except Exception as e:
                logger.warning(f"⚠️ Soft Fail: Could not clear cache for deleting assistant {assistant_id}: {e}")

        # 3. Trending Topics (Soft Fail)
        if self.trending_service:
            try:
                await self.trending_service.delete_assistant_topics(assistant_id)
            except Exception as e:
                logger.warning(f"⚠️ Soft Fail: Could not clear topics for deleting assistant {assistant_id}: {e}")

    def _apply_contrast_logic(self, data: AssistantCreate | AssistantUpdate):
        """Modifies data object in-place to ensure text contrast."""
        if data.avatar_bg_color:
            data.avatar_text_color = calculate_contrast_text_color(data.avatar_bg_color)

    def _validate_image_file(self, file: UploadFile):
        if not file.content_type or not file.content_type.startswith("image/"):
            raise FunctionalError("File must be an image", error_code="INVALID_FILE_TYPE")

    def _get_safe_extension(self, filename: Optional[str]) -> str:
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in ALLOWED_EXTENSIONS:
                return ext
        return DEFAULT_EXTENSION

    async def _cleanup_avatar_file(self, assistant_id: UUID):
        """Offloads file deletion to thread pool."""

        def _delete_sync():
            try:
                for file_path in AVATAR_DIR.glob(f"{assistant_id}.*"):
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"Removed avatar file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup avatar file for {assistant_id}: {e}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _delete_sync)

    async def _save_file_async(self, file: UploadFile, path: Path):
        """Offloads file writing to thread pool."""

        def _save_sync():
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _save_sync)


# Modern Dependency Injection
DBDep = Annotated[AsyncSession, Depends(get_db)]

# Late import to handle potential circular dependencies safely
from app.services.cache_service import SemanticCacheService, get_cache_service


async def get_assistant_service(
    db: DBDep,
    cache_service: Annotated[SemanticCacheService, Depends(get_cache_service)],
    trending_service: Annotated[TrendingService, Depends(get_trending_service)],
) -> AssistantService:
    """Dependency provider for AssistantService."""
    return AssistantService(AssistantRepository(db), cache_service, trending_service)
