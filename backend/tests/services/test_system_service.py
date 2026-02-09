import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import EntityNotFound, TechnicalError
from app.services.system_service import SystemService


@pytest.fixture
def service(tmp_path):
    # whitelist the temp path fixture
    return SystemService(allowed_base_paths=[str(tmp_path)])


@pytest.mark.asyncio
async def test_open_file_externally_blocked_path(service):
    """Verify that unauthorized paths are blocked."""
    with pytest.raises(TechnicalError) as exc:
        await service.open_file_externally("/etc/passwd")  # Assuming /etc/passwd is never in tmp val

    assert exc.value.error_code == "UNAUTHORIZED_PATH_ACCESS"


@pytest.mark.asyncio
async def test_open_file_externally_not_found(service, tmp_path):
    """Verify that missing files in safe paths raise EntityNotFound."""
    safe_file = tmp_path / "missing.txt"
    # Even if path is safe, file non-existence raises EntityNotFound
    # But we mocked exists() in original test?
    # Original: with patch("pathlib.Path.exists", return_value=False):
    # Real logic checks exists().
    # Let's rely on real FS to be safer or mock correctly if we want unit test.
    # The error raised is EntityNotFound.

    with pytest.raises(EntityNotFound):
        await service.open_file_externally(str(safe_file))


@pytest.mark.asyncio
async def test_open_file_externally_success(service, tmp_path):
    """Verify that authorized paths call the sync open logic in a thread."""
    safe_file = tmp_path / "report.pdf"
    # Create the file so resolve() and exists() are happy without mocking if we wanted integration
    # But we mock exists to isolate logic.

    # We must ensure resolve() returns what we expect.
    # On Windows, tmp_path is real.

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.resolve", return_value=safe_file),
        patch("app.services.system_service.asyncio.to_thread", new_callable=AsyncMock) as mock_thread,
    ):

        mock_thread.return_value = True

        success = await service.open_file_externally(str(safe_file))

        assert success is True
        mock_thread.assert_called_once()
        # Verify the first argument to to_thread is the sync helper
        assert mock_thread.call_args[0][0] == service._open_sync
        assert mock_thread.call_args[0][1] == safe_file
