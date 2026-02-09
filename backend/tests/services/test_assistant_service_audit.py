from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.schemas.assistant import AssistantUpdate
from app.services.assistant_service import AssistantService


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.fixture
def service(mock_repo, mock_cache):
    return AssistantService(assistant_repo=mock_repo, cache_service=mock_cache)


@pytest.mark.asyncio
async def test_cleanup_avatar_is_non_blocking(service):
    """
    P0: Verify that _cleanup_avatar_file uses run_in_executor.
    """
    assistant_id = uuid4()

    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        # Provide a future for the awaitable run_in_executor
        mock_loop.run_in_executor.return_value = AsyncMock()
        # Actually run_in_executor returns a future which is awaitable.
        # AsyncMock() is awaitable.

        await service._cleanup_avatar_file(assistant_id)

        # Verify run_in_executor was called
        mock_loop.run_in_executor.assert_called_once()
        # Verify it passed None (default executor) and a callable
        args, _ = mock_loop.run_in_executor.call_args
        assert args[0] is None
        assert callable(args[1])


@pytest.mark.asyncio
async def test_upload_avatar_flow(service, tmp_path):
    """Verify avatar upload logic (mocking I/O internals)."""
    assistant_id = uuid4()
    file_mock = MagicMock(spec=UploadFile)
    file_mock.filename = "test.png"
    file_mock.content_type = "image/png"
    file_mock.file = MagicMock()

    # Mock internal methods to focus on flow
    service._cleanup_avatar_file = AsyncMock()

    # Mock loop for file write
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop

        # We need run_in_executor to actually execute the function?
        # No, just return success.
        mock_loop.run_in_executor.return_value = None

        # Mock Repo update
        updated_assistant = MagicMock()
        updated_assistant.id = assistant_id
        updated_assistant.avatar_image = f"{assistant_id}.png"
        service.assistant_repo.update_with_connectors.return_value = updated_assistant

        result = await service.upload_avatar(assistant_id, file_mock)

        assert result.id == assistant_id
        # Verify cleanup called
        service._cleanup_avatar_file.assert_called_with(assistant_id)
        # Verify repo update
        service.assistant_repo.update_with_connectors.assert_called_once()
