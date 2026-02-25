"""
Dependency Injection Providers - FastAPI dependency functions.

Provides repository and strategy instances for dependency injection in routes.
"""

import logging
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import (
    AnalyticsRepository,
    AssistantRepository,
    ChatHistoryRepository,
    ConnectorRepository,
    DocumentRepository,
    UserRepository,
    VectorRepository,
)
from app.services.vector_service import VectorService, get_vector_service
from app.strategies import HybridStrategy, SearchStrategy, VectorOnlyStrategy

logger = logging.getLogger(__name__)


# ============================================================================
# REPOSITORY PROVIDERS
# ============================================================================


async def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    """Provide UserRepository instance."""
    return UserRepository(db)


async def get_document_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> DocumentRepository:
    """Provide DocumentRepository instance."""
    return DocumentRepository(db)


async def get_connector_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ConnectorRepository:
    """Provide ConnectorRepository instance."""
    return ConnectorRepository(db)


async def get_assistant_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AssistantRepository:
    """Provide AssistantRepository instance."""
    return AssistantRepository(db)


async def get_analytics_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyticsRepository:
    """Provide AnalyticsRepository instance."""
    return AnalyticsRepository(db)


async def get_chat_history_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ChatHistoryRepository:
    """Provide ChatHistoryRepository instance."""
    return ChatHistoryRepository(db)


async def get_vector_repository(vs: Annotated[VectorService, Depends(get_vector_service)]) -> VectorRepository:
    """
    Provide VectorRepository instance.
    Uses async client for non-blocking Qdrant operations.
    """
    qdrant_client = await vs.get_async_qdrant_client()
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
    Factory pattern for strategy injection.
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
AssistantRepositoryDep = Annotated[AssistantRepository, Depends(get_assistant_repository)]
AnalyticsRepositoryDep = Annotated[AnalyticsRepository, Depends(get_analytics_repository)]
ChatHistoryRepositoryDep = Annotated[ChatHistoryRepository, Depends(get_chat_history_repository)]
VectorRepositoryDep = Annotated[VectorRepository, Depends(get_vector_repository)]
SearchStrategyDep = Annotated[SearchStrategy, Depends(get_search_strategy)]
