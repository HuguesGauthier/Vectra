"""
Dependency Injection Providers - FastAPI dependency functions.

Provides repository and strategy instances for dependency injection in routes.
"""

import logging
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import (ConnectorRepository, DocumentRepository,
                              UserRepository, VectorRepository)
from app.services.vector_service import VectorService, get_vector_service
from app.strategies import HybridStrategy, SearchStrategy, VectorOnlyStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# REPOSITORY PROVIDERS
# ============================================================================


async def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    """
    Provide UserRepository instance.

    ARCHITECT NOTE: Dependency Inversion
    Routes depend on this function, not on concrete repository creation.
    Makes testing easier - can mock this function.

    Args:
        db: The asynchronous database session.

    Returns:
        An instance of UserRepository.
    """
    return UserRepository(db)


async def get_document_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> DocumentRepository:
    """
    Provide DocumentRepository instance.

    Args:
        db: The asynchronous database session.

    Returns:
        An instance of DocumentRepository.
    """
    return DocumentRepository(db)


async def get_connector_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ConnectorRepository:
    """
    Provide ConnectorRepository instance.

    Args:
        db: The asynchronous database session.

    Returns:
        An instance of ConnectorRepository.
    """
    return ConnectorRepository(db)


async def get_vector_repository(vs: Annotated[VectorService, Depends(get_vector_service)]) -> VectorRepository:
    """
    Provide VectorRepository instance.

    Note: Vector repository doesn't need AsyncSession,
    it uses the Qdrant client directly.

    Args:
        vs: The vector service instance.

    Returns:
        An instance of VectorRepository using an async Qdrant client.
    """
    # Use Async client to ensure non-blocking IO in strategies
    qdrant_client = vs.get_async_qdrant_client()
    return VectorRepository(qdrant_client)


# ============================================================================
# STRATEGY PROVIDERS
# ============================================================================


def get_search_strategy(
    strategy_type: str = "hybrid",
    vector_repo: Annotated[Optional[VectorRepository], Depends(get_vector_repository)] = None,
    document_repo: Annotated[Optional[DocumentRepository], Depends(get_document_repository)] = None,
    connector_repo: Annotated[Optional[ConnectorRepository], Depends(get_connector_repository)] = None,
    vector_service: Annotated[Optional[VectorService], Depends(get_vector_service)] = None,
) -> SearchStrategy:
    """
    Provide SearchStrategy instance based on type.

    ARCHITECT NOTE: Factory Method Pattern
    Creates appropriate strategy based on runtime parameter.
    Now injects all required dependencies for hardened RAG pipeline.

    Args:
        strategy_type: Type of strategy ('vector_only' or 'hybrid').
        vector_repo: Vector repository instance.
        document_repo: Document repository instance.
        connector_repo: Connector repository instance (for collection resolution).
        vector_service: Vector service instance (for embedding generation).

    Returns:
        Appropriate search strategy instance (VectorOnlyStrategy or HybridStrategy).
    """
    if strategy_type == "vector_only":
        logger.debug("Dependency Injection: Instantiating VectorOnlyStrategy")
        return VectorOnlyStrategy(vector_repo=vector_repo, connector_repo=connector_repo, vector_service=vector_service)
    else:
        logger.debug("Dependency Injection: Instantiating HybridStrategy")
        return HybridStrategy(
            vector_repo=vector_repo,
            document_repo=document_repo,
            connector_repo=connector_repo,
            vector_service=vector_service,
        )


# ============================================================================
# TYPE ALIASES FOR CONVENIENCE
# ============================================================================

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
ConnectorRepositoryDep = Annotated[ConnectorRepository, Depends(get_connector_repository)]
VectorRepositoryDep = Annotated[VectorRepository, Depends(get_vector_repository)]
SearchStrategyDep = Annotated[SearchStrategy, Depends(get_search_strategy)]
