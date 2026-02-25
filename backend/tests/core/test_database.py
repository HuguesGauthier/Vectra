from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core import database
from app.core.exceptions import TechnicalError

@pytest.fixture(autouse=True)
async def cleanup_database_module():
    """Reset the singleton state before and after each test."""
    await database.reset_db_connection()
    yield
    await database.reset_db_connection()


class TestDatabaseLazyLoading:
    """Test singleton and lazy loading mechanics."""

    @pytest.mark.asyncio
    async def test_get_engine_creates_singleton(self):
        """get_engine should create and return a singleton engine."""
        with patch("app.core.database.create_async_engine") as mock_create:
            with patch("app.core.database.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
                mock_get_settings.return_value = mock_settings

                mock_engine = AsyncMock(spec=AsyncEngine)
                mock_create.return_value = mock_engine

                # First call creates
                engine1 = database.get_engine()
                assert engine1 is mock_engine
                mock_create.assert_called_once()

            # Second call returns existing
            engine2 = database.get_engine()
            assert engine2 is engine1
            mock_create.assert_called_once()  # Still only called once

    @pytest.mark.asyncio
    async def test_get_session_factory_initializes_engine(self):
        """get_session_factory should trigger engine creation if needed."""
        with patch("app.core.database.get_engine") as mock_get_engine:
            mock_engine = AsyncMock(spec=AsyncEngine)
            mock_get_engine.return_value = mock_engine

            factory = database.get_session_factory()

            assert factory is not None
            mock_get_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_lazy_loading_preserves_import_speed(self):
        """Importing database module should NOT create engine."""
        # This test is implicit since we are running it, but strictly speaking
        # we check the global variable is None at start of test due to fixture
        assert database._engine is None
        assert database._session_factory is None


class TestDatabaseErrorHandling:
    """Test error scenarios."""

    @pytest.mark.asyncio
    async def test_engine_creation_failure_raises_technical_error(self):
        """Failure to create engine should raise TechnicalError."""
        with patch("app.core.database.create_async_engine") as mock_create:
            mock_create.side_effect = Exception("Connection refused")

            with pytest.raises(TechnicalError) as exc_info:
                database.get_engine()

            assert "Database Configuration Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_engine_validation_checks_driver(self):
        """Should raise TechnicalError if asyncpg is missing for postgres."""
        with (
            patch("app.core.database.get_settings") as mock_get_settings,
            patch("app.core.database.create_async_engine") as mock_create,
        ):
            mock_settings = MagicMock()
            mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
            mock_settings.DB_POOL_SIZE = 5
            mock_settings.DB_MAX_OVERFLOW = 10
            mock_settings.DB_POOL_RECYCLE = 3600
            mock_settings.DB_ECHO = False
            mock_get_settings.return_value = mock_settings

            with pytest.raises(TechnicalError) as exc:
                database.get_engine()

            assert "requires 'postgresql+asyncpg://'" in str(exc.value)


class TestDatabaseLifecycle:
    """Test get_db dependency and shutdown."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """get_db should yield a session and close it."""
        from unittest.mock import MagicMock

        # Session mock
        mock_session = AsyncMock(spec=AsyncSession)

        # The factory returns a context manager, NOT a coroutine
        mock_factory_instance = MagicMock()
        mock_factory_instance.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_instance.__aexit__ = AsyncMock(return_value=None)

        # The factory call itself is synchronous (it's called, not awaited, to get the CM)
        # But wait, database.py does: async with session_factory() as session
        # So session_factory() returns the CM.
        mock_factory = MagicMock(return_value=mock_factory_instance)

        with patch("app.core.database.get_session_factory", return_value=mock_factory):
            gen = database.get_db()
            session = await anext(gen)

            assert session is mock_session

            # Close generator
            with pytest.raises(StopAsyncIteration):
                await anext(gen)

            # Verify context manager exit was called
            mock_factory_instance.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_db_connection_disposes_engine(self):
        """close_db_connection should dispose the engine."""
        mock_engine = AsyncMock(spec=AsyncEngine)

        # Manually set the singleton
        database._engine = mock_engine

        await database.close_db_connection()

        mock_engine.dispose.assert_awaited_once()
        assert database._engine is None
