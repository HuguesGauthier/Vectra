import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import TechnicalError
from app.core.settings import get_settings

logger = logging.getLogger(__name__)

# Singleton holders (Lazy Loading)
# Global mutable state is minimized and controlled via getters
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """
    Get or create the async database engine (Singleton).
    Lazy initialization prevents side-effects at import time.
    """
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    try:
        url = make_url(settings.DATABASE_URL)

        # P3: Robust Driver Check
        if url.get_backend_name() == "postgresql" and "asyncpg" not in url.drivername:
            raise TechnicalError("Database Configuration Error: Async engine requires 'postgresql+asyncpg://' driver.")

        logger.info(f"🔌 Connecting to Database pool: {settings.DB_POOL_SIZE} connections.")
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            echo=settings.DB_ECHO,
        )
        return _engine
    except Exception as e:
        logger.critical(f"❌ Database Engine Creation Failed: {e}")
        # P1: Avoid sys.exit(), raise typed exception instead
        raise TechnicalError(f"Database Configuration Error: {e}")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the session factory (Singleton).
    """
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = get_engine()
    _session_factory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        # P1: Critical for async to prevent implicit I/O in schemas
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return _session_factory


def SessionLocal() -> AsyncSession:
    """
    Compatibility wrapper for lazy loaded session factory.
    Returns a new AsyncSession instance.
    """
    factory = get_session_factory()
    return factory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency for database sessions.
    Handles lifecycle: connect -> yield -> [commit/rollback] -> close.

    P2: Removed useless try/except. Context manager handles rollback automatically.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session


async def close_db_connection():
    """
    P3: Clean resource cleanup.
    Should be called on Application Shutdown.
    """
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("🔌 Database connection closed.")


async def reset_db_connection():
    """
    Helper for testing to force reconnection.
    """
    await close_db_connection()
    global _session_factory
    _session_factory = None
