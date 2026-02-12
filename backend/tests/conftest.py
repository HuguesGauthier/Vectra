import sys
from unittest.mock import AsyncMock, MagicMock

# Mock pyodbc before any app imports
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()
psutil_mock = MagicMock()
psutil_mock.__spec__ = MagicMock()
sys.modules["psutil"] = psutil_mock

# Global settings mock for tests that rely on app.core.settings
settings_mock = MagicMock()
settings_mock.DB_HOST = "localhost"
settings_mock.DB_USER = "sa"
settings_mock.DB_PASSWORD = "password"
settings_mock.DB_NAME = "testdb"
settings_mock.LOG_LEVEL = "INFO"
settings_mock.DEBUG = False
settings_mock.QDRANT_HOST = "localhost"
settings_mock.QDRANT_API_KEY = "test_key"

# Create a module mock that has a 'settings' attribute
settings_module_mock = MagicMock()
settings_module_mock.settings = settings_mock
sys.modules["app.core.settings"] = settings_module_mock

import pytest


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
