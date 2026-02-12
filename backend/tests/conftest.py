import sys
from unittest.mock import AsyncMock, MagicMock

# Mock pyodbc before any app imports
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

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
