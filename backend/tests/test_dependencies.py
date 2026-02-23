import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from typing import Annotated

# Mock dependencies globally
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import (
    get_user_repository,
    get_document_repository,
    get_connector_repository,
    get_assistant_repository,
    get_analytics_repository,
    get_chat_history_repository,
    get_vector_repository,
    get_search_strategy,
)
from app.repositories import (
    UserRepository,
    DocumentRepository,
    ConnectorRepository,
    AssistantRepository,
    AnalyticsRepository,
    ChatHistoryRepository,
    VectorRepository,
)
from app.services.vector_service import VectorService
from app.strategies import HybridStrategy, VectorOnlyStrategy


@pytest.mark.asyncio
async def test_repository_providers():
    """Happy Path: Verify each provider returns the correct repository type."""
    mock_db = MagicMock(spec=AsyncSession)

    # Test DB-based repositories
    assert isinstance(await get_user_repository(mock_db), UserRepository)
    assert isinstance(await get_document_repository(mock_db), DocumentRepository)
    assert isinstance(await get_connector_repository(mock_db), ConnectorRepository)
    assert isinstance(await get_assistant_repository(mock_db), AssistantRepository)
    assert isinstance(await get_analytics_repository(mock_db), AnalyticsRepository)
    assert isinstance(await get_chat_history_repository(mock_db), ChatHistoryRepository)


@pytest.mark.asyncio
async def test_vector_repository_provider():
    """Happy Path: Verify vector repository provider."""
    mock_vs = MagicMock(spec=VectorService)
    mock_vs.get_async_qdrant_client = AsyncMock(return_value=MagicMock())

    repo = await get_vector_repository(mock_vs)
    assert isinstance(repo, VectorRepository)
    mock_vs.get_async_qdrant_client.assert_called_once()


def test_get_search_strategy_factory():
    """Happy Path: Verify factory pattern for search strategies."""
    mock_vector_repo = MagicMock(spec=VectorRepository)
    mock_doc_repo = MagicMock(spec=DocumentRepository)
    mock_conn_repo = MagicMock(spec=ConnectorRepository)
    mock_vs = MagicMock(spec=VectorService)

    # Test Hybrid (default)
    strategy = get_search_strategy(
        strategy_type="hybrid",
        vector_repo=mock_vector_repo,
        document_repo=mock_doc_repo,
        connector_repo=mock_conn_repo,
        vector_service=mock_vs,
    )
    assert isinstance(strategy, HybridStrategy)

    # Test Vector Only
    strategy = get_search_strategy(
        strategy_type="vector_only",
        vector_repo=mock_vector_repo,
        document_repo=mock_doc_repo,
        connector_repo=mock_conn_repo,
        vector_service=mock_vs,
    )
    assert isinstance(strategy, VectorOnlyStrategy)
