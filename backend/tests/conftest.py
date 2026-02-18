import sys
import pytest
from unittest.mock import AsyncMock, MagicMock

# Mock pyodbc before any app imports
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()
psutil_mock = MagicMock()
psutil_mock.__spec__ = MagicMock()
sys.modules["psutil"] = psutil_mock

# Global settings mock for tests that rely on app.core.settings
@pytest.fixture(scope="session")
def settings_mock():
    mock = MagicMock()
    mock.ENV = "test"
    mock.DEBUG = False
    mock.DATABASE_URL = "postgresql+asyncpg://vectra:vectra@localhost:5432/vectra"
    mock.DB_HOST = "localhost"
    mock.DB_USER = "sa"
    mock.DB_PASSWORD = "password"
    mock.DB_NAME = "testdb"
    mock.DB_POOL_SIZE = 20
    mock.DB_MAX_OVERFLOW = 10
    mock.DB_POOL_RECYCLE = 3630
    mock.DB_ECHO = False
    mock.LOG_LEVEL = "INFO"
    mock.QDRANT_HOST = "localhost"
    mock.QDRANT_API_KEY = "test_key"
    mock.WORKER_SECRET = "test-worker-secret-ephemeral-32-chars-long"
    mock.SECRET_KEY = "test-secret-key-ephemeral-32-chars-long"

    return mock



@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock()
    return session
