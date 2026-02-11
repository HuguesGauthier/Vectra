import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch
import sys

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.analytics_repository import AnalyticsRepository
from app.models.usage_stat import UsageStat
from app.models.connector_document import ConnectorDocument
from app.models.connector import Connector


@pytest.mark.asyncio
async def test_get_document_retrieval_stats_execution():
    """
    Verifies that the SQL in get_document_retrieval_stats is syntactically correct
    by checking if it executes against a mock session.
    """
    mock_db = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute.return_value = mock_result

    repo = AnalyticsRepository(mock_db)
    cutoff = datetime.now(timezone.utc)

    # This should not raise ProgrammingError or UndefinedTableError
    results = await repo.get_document_retrieval_stats(cutoff, limit=10)

    assert results == []
    mock_db.execute.assert_called_once()

    # Verify the SQL used the correct table name
    args, kwargs = mock_db.execute.call_args
    sql_text = str(args[0])
    assert "connectors_documents" in sql_text
    assert "connector_documents" not in sql_text
    assert "CROSS JOIN LATERAL" in sql_text
