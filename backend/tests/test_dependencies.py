"""
Unit tests for dependencies.py.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies import (HybridStrategy, VectorOnlyStrategy,
                              get_connector_repository,
                              get_document_repository, get_search_strategy,
                              get_user_repository, get_vector_repository)


@pytest.mark.asyncio
async def test_get_repositories():
    """✅ SUCCESS: Repositories are correctly instantiated."""
    mock_db = AsyncMock()

    user_repo = await get_user_repository(mock_db)
    doc_repo = await get_document_repository(mock_db)
    con_repo = await get_connector_repository(mock_db)

    assert user_repo.db == mock_db
    assert doc_repo.db == mock_db
    assert con_repo.db == mock_db


@pytest.mark.asyncio
async def test_get_vector_repository():
    """✅ SUCCESS: Vector Repo gets client from service."""
    mock_vs = MagicMock()
    mock_vs.get_async_qdrant_client.return_value = "mock_client"

    repo = await get_vector_repository(mock_vs)
    assert repo.client == "mock_client"


def test_get_search_strategy_hybrid():
    """✅ SUCCESS: Hybrid Strategy instantiated with all dependencies."""
    mock_v_repo = MagicMock()
    mock_d_repo = MagicMock()
    mock_c_repo = MagicMock()
    mock_vs = MagicMock()

    strategy = get_search_strategy(
        strategy_type="hybrid",
        vector_repo=mock_v_repo,
        document_repo=mock_d_repo,
        connector_repo=mock_c_repo,
        vector_service=mock_vs,
    )

    assert isinstance(strategy, HybridStrategy)
    assert strategy.vector_repo == mock_v_repo
    assert strategy.document_repo == mock_d_repo
    assert strategy.connector_repo == mock_c_repo
    assert strategy.vector_service == mock_vs


def test_get_search_strategy_vector_only():
    """✅ SUCCESS: Vector Strategy instantiated with subset of dependencies."""
    mock_v_repo = MagicMock()
    mock_c_repo = MagicMock()
    mock_vs = MagicMock()

    strategy = get_search_strategy(
        strategy_type="vector_only",
        vector_repo=mock_v_repo,
        document_repo=None,  # Not needed
        connector_repo=mock_c_repo,
        vector_service=mock_vs,
    )

    assert isinstance(strategy, VectorOnlyStrategy)
    assert strategy.vector_repo == mock_v_repo
    assert strategy.connector_repo == mock_c_repo
    assert strategy.vector_service == mock_vs
