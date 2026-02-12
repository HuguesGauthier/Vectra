from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import TechnicalError
from app.core.init_db import init_db
from app.models.user import User


@pytest.mark.asyncio
class TestInitDb:

    async def test_init_db_creates_admin_if_not_exists(self):
        """Should create admin user if not present."""
        # Mock Session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # User not found
        mock_session.execute.return_value = mock_result

        # Mock Session Context Manager
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.init_db.SessionLocal", return_value=mock_cm):
            # Patch get_settings to return a mock with expected attributes
            mock_settings = MagicMock()
            mock_settings.FIRST_SUPERUSER = "admin@test.ai"
            mock_settings.FIRST_SUPERUSER_PASSWORD = "password"

            with patch("app.core.init_db.get_settings", return_value=mock_settings):
                with patch("app.core.init_db.run_in_threadpool", new_callable=AsyncMock) as mock_run_pool:
                    mock_run_pool.return_value = "hashed_secret"

                    await init_db()

                    # Verify execute called (check existing)
                    mock_session.execute.assert_awaited()

                    # Verify hashing called via threadpool
                    mock_run_pool.assert_awaited()

                    # Verify add and commit
                    mock_session.add.assert_called_once()
                    args, _ = mock_session.add.call_args
                    added_user = args[0]
                    assert isinstance(added_user, User)
                    assert added_user.role == "admin"
                    assert added_user.hashed_password == "hashed_secret"

                    mock_session.commit.assert_awaited_once()

    async def test_init_db_skips_creation_if_exists(self):
        """Should not create admin if already exists."""
        # Mock Session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_user = User(email="admin@vectra.ai", role="admin")
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Mock Session Context Manager
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.init_db.SessionLocal", return_value=mock_cm):
            mock_settings = MagicMock()
            mock_settings.FIRST_SUPERUSER = "admin@test.ai"

            with patch("app.core.init_db.get_settings", return_value=mock_settings):
                # We don't need to patch run_in_threadpool because it shouldn't be called
                with patch("app.core.init_db.run_in_threadpool", new_callable=AsyncMock) as mock_run_pool:
                    await init_db()

                    mock_session.execute.assert_awaited()
                    mock_run_pool.assert_not_awaited()
                    mock_session.add.assert_not_called()
                    mock_session.commit.assert_not_awaited()

    async def test_init_db_handles_db_error(self):
        """Should raise TechnicalError on DB failure."""
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=SQLAlchemyError("Connection Error"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.init_db.SessionLocal", return_value=mock_cm):
            with patch("app.core.init_db.get_settings", return_value=MagicMock()):
                with pytest.raises(TechnicalError) as exc_info:
                    await init_db()

                assert "Failed to initialize database" in str(exc_info.value)

    async def test_init_db_handles_generic_error(self):
        """Should raise TechnicalError on unexpected failure."""
        with patch("app.core.init_db.get_settings", side_effect=Exception("Major failure")):
            with pytest.raises(TechnicalError) as exc_info:
                await init_db()
            assert "Unexpected error during database initialization" in str(exc_info.value)
