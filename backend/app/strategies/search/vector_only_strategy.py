"""
Vector-Only Search Strategy - Pure semantic search via Qdrant.

Uses only vector similarity for search, no SQL metadata filtering.
Hardened for production with strict validation and dependency injection.
"""

import logging
from typing import Annotated, Any, Optional
from uuid import UUID

from pydantic import Field
from qdrant_client.http import models

from app.repositories.connector_repository import ConnectorRepository
from app.repositories.vector_repository import VectorRepository
from app.services.vector_service import VectorService
from app.strategies.search.base import (DEFAULT_TOP_K, MAX_QUERY_LENGTH,
                                        MAX_TOP_K, SearchExecutionError,
                                        SearchFilters, SearchMetadata,
                                        SearchResult, SearchStrategy)

logger = logging.getLogger(__name__)


class VectorOnlyStrategy(SearchStrategy):
    """
    Pure vector search strategy.

    ARCHITECT NOTE: Single Responsibility
    This strategy focuses purely on semantic similarity search.
    It performs:
    1. Collection Resolution
    2. Query Vectorization
    3. Vector Retrieval (Qdrant)
    """

    def __init__(
        self, vector_repo: VectorRepository, connector_repo: ConnectorRepository, vector_service: VectorService
    ):
        """
        Initialize with dependencies.

        Args:
            vector_repo: Qdrant DAO
            connector_repo: To resolve provider/collection
            vector_service: To embed queries
        """
        super().__init__()
        self.vector_repo = vector_repo
        self.connector_repo = connector_repo
        self.vector_service = vector_service

    async def search(
        self,
        query: Annotated[str, Field(min_length=1, max_length=MAX_QUERY_LENGTH)],
        top_k: Annotated[int, Field(ge=1, le=MAX_TOP_K)] = DEFAULT_TOP_K,
        filters: Optional[SearchFilters] = None,
    ) -> list[SearchResult]:
        """
        Execute pure vector search in Qdrant.
        """
        self._log_search_start(query, top_k)

        try:
            # 1. Resolve Collection
            collection_name = await self._resolve_collection(filters)

            # 2. Vectorize Query (Async/Non-blocking)
            # VectorService handles model loading and threading internally
            embedding_model = await self.vector_service.get_embedding_model()
            query_vector = await embedding_model.aget_query_embedding(query)

            # 2.5 Build Pre-Filter (ACLs)
            qdrant_filter = self._build_qdrant_filter(filters)

            # 3. Execute Search
            # Uses Repository abstraction
            hits = await self.vector_repo.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False,
            )

            # 4. Map Results
            results = []
            for hit in hits:
                payload = hit.payload or {}
                doc_id_str = payload.get("connector_document_id")

                if not doc_id_str:
                    logger.warning(f"Vector hit missing document_id: {hit.id}")
                    continue

                try:
                    doc_id = UUID(doc_id_str)

                    result = SearchResult(
                        document_id=doc_id,
                        score=hit.score,
                        content=payload.get("content", "")[:100000],  # Truncate safety
                        metadata=SearchMetadata(
                            file_name=payload.get("file_name"),
                            file_path=payload.get("file_path"),
                            connector_name=payload.get("connector_name"),
                        ),
                    )
                    results.append(result)
                except ValueError:
                    logger.warning(f"Invalid UUID in vector payload: {doc_id_str}")
                    continue

            self._log_search_complete(len(results), 0)
            return results

        except Exception as e:
            self._log_search_error(e)
            raise SearchExecutionError(f"Vector search failed: {e}") from e

    async def _resolve_collection(self, filters: Optional[SearchFilters]) -> str:
        """Resolve Qdrant collection name."""
        if not filters or not filters.connector_id:
            # Fallback to default
            return await self.vector_service.get_collection_name(provider="openai")

        connector = await self.connector_repo.get_by_id(filters.connector_id)
        if not connector:
            raise SearchExecutionError(f"Connector {filters.connector_id} not found")

        # Get provider from connector config
        provider = connector.configuration.get("ai_provider", "openai")
        return await self.vector_service.get_collection_name(provider=provider)

    def _build_qdrant_filter(self, filters: Optional[SearchFilters]) -> Optional[models.Filter]:
        """
        Construct Qdrant Filter for Pre-Filtering (ACLs).
        """
        if not filters:
            return None

        conditions = []

        # ACL Filter
        if filters.user_acl:
            conditions.append(models.FieldCondition(key="connector_acl", match=models.MatchAny(any=filters.user_acl)))

        if not conditions:
            return None

        return models.Filter(must=conditions)

    @property
    def strategy_name(self) -> str:
        return "VectorOnly"
