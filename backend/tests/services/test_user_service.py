import sys
from unittest.mock import MagicMock

# Mock environmental dependencies to unblock tests
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()
sys.modules["vanna.remote"] = MagicMock()

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
from fastapi import UploadFile
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import EntityNotFound, FunctionalError


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.email_exists = AsyncMock()
    repo.create = AsyncMock()
    repo.get = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def service(mock_db, mock_repository):
    svc = UserService(db=mock_db)
    svc.repository = mock_repository
    return svc


@pytest.mark.asyncio
async def test_create_user_success(service, mock_repository):
    # Setup
    user_in = UserCreate(email="test@example.com", password="securepassword", role="user")
    mock_repository.email_exists.return_value = False
    async def _create_side_effect(u): return u
    mock_repository.create.side_effect = _create_side_effect

    # Execute
    user = await service.create(user_in)

    # Verify
    assert user.email == user_in.email
    assert user.hashed_password != user_in.password
    mock_repository.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(service, mock_repository):
    # Setup
    user_in = UserCreate(email="exists@example.com", password="securepassword", role="user")
    mock_repository.email_exists.return_value = True

    # Execute & Verify
    with pytest.raises(FunctionalError) as excinfo:
        await service.create(user_in)
    assert excinfo.value.error_code == "USER_EXISTS"


@pytest.mark.asyncio
async def test_get_by_id_not_found(service, mock_repository):
    # Setup
    u_id = uuid4()
    mock_repository.get.return_value = None

    # Execute & Verify
    with pytest.raises(EntityNotFound):
        await service.get_by_id(u_id)


@pytest.mark.asyncio
async def test_update_user_password(service, mock_repository):
    # Setup
    u_id = uuid4()
    mock_user = MagicMock(spec=User)
    mock_repository.get.return_value = mock_user

    user_update = UserUpdate(password="newsecurepassword")

    # Execute
    await service.update(u_id, user_update)

    # Verify
    args, kwargs = mock_repository.update.call_args
    assert "hashed_password" in args[1]
    assert "password" not in args[1]


@pytest.mark.asyncio
async def test_upload_avatar_success(service, mock_repository):
    # Setup
    u_id = uuid4()
    mock_file = MagicMock(spec=UploadFile)
    mock_file.content_type = "image/png"
    mock_file.filename = "avatar.png"
    mock_file.file = MagicMock()
    mock_file.file.tell.return_value = 1024  # 1KB

    # Mocking disk I/O and loop
    with patch("app.services.user_service.AVATAR_DIR") as mock_dir:
        mock_dir.exists.return_value = True
        with patch.object(asyncio.get_running_loop(), "run_in_executor", new_callable=AsyncMock) as mock_executor:
            # Execute
            await service.upload_avatar(u_id, mock_file)

            # Verify
            assert mock_executor.call_count >= 2  # mkdir, cleanup, save
            mock_repository.update.assert_called_once()
            args, kwargs = mock_repository.update.call_args
            assert args[1]["avatar_url"] == f"/users/{u_id}/avatar"


@pytest.mark.asyncio
async def test_get_avatar_path_found(service, mock_repository):
    # Setup
    u_id = uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.avatar_url = f"/users/{u_id}/avatar"
    mock_repository.get.return_value = mock_user

    mock_path = MagicMock(spec=Path)

    with patch("app.services.user_service.AVATAR_DIR") as mock_dir:
        mock_dir.glob.return_value = [mock_path]

        # Execute
        path = await service.get_avatar_path(u_id)

        # Verify
        assert path == mock_path
