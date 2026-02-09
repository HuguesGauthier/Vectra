import logging
from typing import Annotated, Dict, List, Optional
from uuid import UUID

from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status)
from fastapi.responses import FileResponse

from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.core.security import get_current_admin, get_current_user_optional
from app.models.user import User
from app.schemas.assistant import (AssistantCreate, AssistantResponse,
                                   AssistantUpdate)
from app.services.assistant_service import (AssistantService,
                                            get_assistant_service)

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[AssistantResponse])
async def get_assistants(
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[AssistantResponse]:
    """
    List all assistants.

    Public access allowed but filtered for guests. Private assistants are excluded
    if no user is authenticated.

    Args:
        service: Assistant service instance.
        user: Current optional user.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A list of assistant response objects.

    Raises:
        TechnicalError: If fetching assistants fails.
    """
    # Filter: If User is missing (Guest), exclude private assistants.
    exclude_private = user is None

    try:
        # TODO: Refactor Service to support DB-side pagination (P1)
        # Passing exclude_private to service layer
        assistants = await service.get_assistants(exclude_private=exclude_private)

        # Manual Slicing (Temporary P2 solution)
        return assistants[skip : skip + limit]

    except Exception as e:
        logger.error(f"Failed to fetch assistants: {e}", exc_info=True)
        raise TechnicalError(f"Failed to fetch assistants: {e}")


@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> AssistantResponse:
    """
    Get a single assistant by ID.

    Args:
        assistant_id: Unique identifier of the assistant.
        service: Assistant service instance.
        user: Current optional user.

    Returns:
        The assistant response object.

    Raises:
        EntityNotFound: If the assistant does not exist.
        HTTPException: If authentication is required but user is not logged in.
        TechnicalError: If fetching the assistant fails.
    """
    try:
        assistant = await service.get_assistant(assistant_id)
        if not assistant:
            raise EntityNotFound("Assistant not found")

        # Access Control: If assistant requires authentication, user must be logged in.
        if assistant.user_authentication and not user:
            logger.warning(f"Access denied for assistant {assistant_id}: User Authentication Required")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for this assistant",
            )

        return assistant

    except (EntityNotFound, HTTPException):
        raise
    except Exception as e:
        logger.error(f"Failed to fetch assistant {assistant_id}: {e}", exc_info=True)
        raise TechnicalError(f"Failed to fetch assistant: {e}")


@router.post("/", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    assistant: AssistantCreate,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> AssistantResponse:
    """
    Create a new assistant (Admin only).

    Args:
        assistant: Assistant creation data.
        service: Assistant service instance.
        current_user: Current authenticated admin user.

    Returns:
        The created assistant response object.

    Raises:
        FunctionalError: If there is a validation or functional error.
        TechnicalError: If creating the assistant fails.
    """
    try:
        return await service.create_assistant(assistant)
    except Exception as e:
        logger.error(f"Failed to create assistant: {e}", exc_info=True)
        if isinstance(e, (FunctionalError, TechnicalError)):
            raise
        raise TechnicalError(f"Failed to create assistant: {e}")


@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    assistant: AssistantUpdate,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> AssistantResponse:
    """
    Update an existing assistant (Admin only).

    Args:
        assistant_id: Unique identifier of the assistant to update.
        assistant: Assistant update data.
        service: Assistant service instance.
        current_user: Current authenticated admin user.

    Returns:
        The updated assistant response object.

    Raises:
        EntityNotFound: If the assistant does not exist.
        FunctionalError: If there is a validation or functional error.
        TechnicalError: If updating the assistant fails.
    """
    try:
        updated_assistant = await service.update_assistant(assistant_id, assistant)
        if not updated_assistant:
            raise EntityNotFound("Assistant not found")
        return updated_assistant
    except (EntityNotFound, FunctionalError, TechnicalError):
        raise
    except Exception as e:
        logger.error(f"Failed to update assistant {assistant_id}: {e}", exc_info=True)
        raise TechnicalError(f"Failed to update assistant: {e}")


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> None:
    """
    Delete an assistant (Admin only).

    Args:
        assistant_id: Unique identifier of the assistant to delete.
        service: Assistant service instance.
        current_user: Current authenticated admin user.

    Raises:
        EntityNotFound: If the assistant does not exist.
        TechnicalError: If deleting the assistant fails.
    """
    try:
        success = await service.delete_assistant(assistant_id)
        if not success:
            raise EntityNotFound("Assistant not found")
        return  # 204 No Content
    except EntityNotFound:
        raise
    except Exception as e:
        logger.error(f"Failed to delete assistant {assistant_id}: {e}", exc_info=True)
        raise TechnicalError(f"Failed to delete assistant: {e}")


@router.post("/{assistant_id}/avatar", response_model=AssistantResponse)
async def upload_assistant_avatar(
    assistant_id: UUID,
    file: UploadFile = File(...),
    service: Annotated[AssistantService, Depends(get_assistant_service)] = None,
    current_user: Annotated[User, Depends(get_current_admin)] = None,
) -> AssistantResponse:
    """
    Upload an avatar image for the assistant.

    Args:
        assistant_id: Unique identifier of the assistant.
        file: The image file to upload.
        service: Assistant service instance.
        current_user: Current authenticated admin user.

    Returns:
        The updated assistant response object with new avatar.

    Raises:
        FunctionalError: If the file is invalid or not an image.
        TechnicalError: If uploading the avatar fails.
    """
    try:
        # P0: Security Check - Ensure assistant exists implicitly via Service,
        # but explicit check helps return 404 cleanly before processing file.
        # Service handles this update logic internally via DB constraint or check.
        return await service.upload_avatar(assistant_id, file)
    except Exception as e:
        logger.error(f"Failed to upload avatar: {e}", exc_info=True)
        if isinstance(e, (FunctionalError, TechnicalError)):
            raise
        raise TechnicalError(f"Failed to upload avatar: {e}")


@router.delete("/{assistant_id}/avatar", response_model=AssistantResponse)
async def delete_assistant_avatar(
    assistant_id: UUID,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> AssistantResponse:
    """
    Remove the avatar image from the assistant.

    Args:
        assistant_id: Unique identifier of the assistant.
        service: Assistant service instance.
        current_user: Current authenticated admin user.

    Returns:
        The updated assistant response object.

    Raises:
        TechnicalError: If removing the avatar fails.
    """
    try:
        return await service.remove_avatar(assistant_id)
    except Exception as e:
        logger.error(f"Failed to remove avatar: {e}", exc_info=True)
        if isinstance(e, (FunctionalError, TechnicalError)):
            raise
        raise TechnicalError(f"Failed to remove avatar: {e}")


@router.get("/{assistant_id}/avatar")
async def get_assistant_avatar(
    assistant_id: UUID,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> FileResponse:
    """
    Get the avatar image file.

    Args:
        assistant_id: Unique identifier of the assistant.
        service: Assistant service instance.
        user: Current optional user.

    Returns:
        The avatar image file response.

    Raises:
        HTTPException: If the avatar or assistant is not found (404).
        TechnicalError: If fetching the avatar fails.
    """
    try:
        # P0: Check Access Control before serving file
        # Retrieve assistant first (lightweight DB fetch)
        assistant = await service.get_assistant(assistant_id)
        if not assistant:
            raise EntityNotFound("Avatar not found")  # Or Assistant not found

        if assistant.user_authentication and not user:
            # Private assistant -> Private avatar
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")  # Obfuscate existence

        file_path = await service.get_avatar_path(assistant_id)
        if not file_path:
            raise EntityNotFound("Avatar not found")

        return FileResponse(file_path)
    except EntityNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get avatar: {e}", exc_info=True)
        raise TechnicalError(f"Failed to get avatar: {e}")


@router.delete("/{assistant_id}/cache", response_model=Dict[str, int])
async def clear_assistant_cache(
    assistant_id: UUID,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, int]:
    """
    Manually purge the semantic cache for a specific assistant.

    Useful when documents are updated or LLM instructions change.

    Args:
        assistant_id: Unique identifier of the assistant.
        service: Assistant service instance.
        current_user: Current authenticated admin user.

    Returns:
        A dictionary containing the number of deleted cache entries.

    Raises:
        TechnicalError: If clearing the cache fails.
    """
    try:
        count = await service.clear_cache(assistant_id)
        return {"deleted_count": count}
    except Exception as e:
        logger.error(f"Failed to clear cache for assistant {assistant_id}: {e}", exc_info=True)
        if isinstance(e, (FunctionalError, TechnicalError)):
            raise
        raise TechnicalError(f"Failed to clear cache: {e}")
