import logging
from typing import Annotated, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.enums import UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService, get_user_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserRead)
async def read_user_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Get current user.

    Args:
        current_user: The currently authenticated user.

    Returns:
        User: The current user object.
    """
    return current_user


@router.get("/", response_model=List[UserRead])
async def read_users(
    service: Annotated[UserService, Depends(get_user_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """
    Retrieve users. Admin only.

    Args:
        service: The user service instance.
        current_admin: The currently authenticated admin user.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        List[User]: A list of users.
    """
    return await service.get_multi(skip=skip, limit=limit)


@router.post("/", response_model=UserRead)
async def create_user(
    *,
    user_in: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> User:
    """
    Create new user. Admin only.

    Args:
        user_in: The user creation data.
        service: The user service instance.
        current_admin: The currently authenticated admin user.

    Returns:
        User: The created user object.
    """
    return await service.create(user_in)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    *,
    user_id: UUID,
    user_in: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> User:
    """
    Update a user. Admin only.

    Args:
        user_id: The ID of the user to update.
        user_in: The user update data.
        service: The user service instance.
        current_admin: The currently authenticated admin user.

    Returns:
        User: The updated user object.
    """
    return await service.update(user_id, user_in)


@router.delete("/{user_id}", response_model=UserRead)
async def delete_user(
    *,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> User:
    """
    Delete a user. Admin only.

    Args:
        user_id: The ID of the user to delete.
        service: The user service instance.
        current_admin: The currently authenticated admin user.

    Returns:
        User: The deleted user object.
    """
    return await service.delete(user_id)


@router.post("/{user_id}/avatar", response_model=UserRead)
async def upload_user_avatar(
    *,
    user_id: UUID,
    file: UploadFile = File(...),
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Upload an avatar image for a user.

    Args:
        user_id: The ID of the user.
        file: The avatar image file to upload.
        service: The user service instance.
        current_user: The currently authenticated user.

    Raises:
        HTTPException: If the user is not authorized.

    Returns:
        User: The updated user object.
    """
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await service.upload_avatar(user_id, file)


@router.delete("/{user_id}/avatar", response_model=UserRead)
async def delete_user_avatar(
    *,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Remove the avatar image from a user.

    Args:
        user_id: The ID of the user.
        service: The user service instance.
        current_user: The currently authenticated user.

    Raises:
        HTTPException: If the user is not authorized.

    Returns:
        User: The updated user object.
    """
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await service.remove_avatar(user_id)


@router.get("/{user_id}/avatar")
async def get_user_avatar(
    *,
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> FileResponse:
    """
    Get the avatar image file for a user.

    Args:
        user_id: The ID of the user.
        service: The user service instance.

    Raises:
        HTTPException: If the avatar is not found.

    Returns:
        FileResponse: The avatar image file.
    """
    file_path = await service.get_avatar_path(user_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Avatar not found")

    return FileResponse(file_path)
