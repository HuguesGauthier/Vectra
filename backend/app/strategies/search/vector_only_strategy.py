import asyncio
import logging
from typing import Annotated, Any, List, Optional
from uuid import UUID

from pydantic import Field
from qdrant_client.http import models

from app.repositories.connector_repository import ConnectorRepository
from app.repositories.vector_repository import VectorRepository
from app.services.vector_service import VectorService
from app.strategies.search.base import (
    DEFAULT_TOP_K,
    MAX_QUERY_LENGTH,
    MAX_TOP_K,
    SearchExecutionError,
    SearchFilters,
    SearchMetadata,
    SearchResult,
    SearchStrategy,
)

logger = logging.getLogger(__name__)

# Constants
CANDIDATE_MULTIPLIER = 1  # No SQL filtering, no need for extra candidates


class VectorOnlyStrategy(SearchStrategy):
    """
    Pure vector search strategy with multi-collection support.

    ARCHITECT NOTE: Pipeline Execution
    1. Resolve Collections (via Connectors)
    2. Vectorize Query (via VectorService)
    3. Retrieval (Qdrant) in parallel
    4. Merge and Ranking
    """

    def __init__(
        self,
        vector_repo: VectorRepository,
        connector_repo: ConnectorRepository,
        vector_service: VectorService,
    ):
        """
        Initialize with dependencies.
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
        Execute parallel vector search across multiple collections.
        """
        self._log_search_start(query, top_k)

        try:
            # 1. Resolve Collections
            collections_info = await self._resolve_collections(filters)

            if not collections_info:
                logger.warning("No collections resolved for search")
                self._log_search_complete(0, 0)
                return []

            # 2. Build Pre-Filter (ACLs only)
            qdrant_filter = self._build_qdrant_filter(filters)

            # 3. Query all collections in parallel
            search_tasks = []
            for coll_info in collections_info:
                task = self._search_single_collection(
                    collection_name=coll_info["name"],
                    provider=coll_info["provider"],
                    query=query,
                    top_k=top_k,
                    qdrant_filter=qdrant_filter,
                )
                search_tasks.append(task)

            all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # 4. Merge results
            merged_results = []
            for idx, result in enumerate(all_results):
                if isinstance(result, Exception):
                    logger.error(f"Error searching collection {collections_info[idx]['name']}: {result}")
                    continue
                merged_results.extend(result)

            if not merged_results:
                self._log_search_complete(0, 0)
                return []

            # 5. Sort by score and limit
            merged_results.sort(key=lambda x: x.score, reverse=True)
            final_results = merged_results[:top_k]

            self._log_search_complete(len(final_results), 0)
            return final_results

        except Exception as e:
            self._log_search_error(e)
            if isinstance(e, SearchExecutionError):
                raise
            raise SearchExecutionError(f"Vector search pipeline failed: {e}") from e

    async def _search_single_collection(
        self, collection_name: str, provider: str, query: str, top_k: int, qdrant_filter: Optional[Any]
    ) -> list[SearchResult]:
        """
        Search a single collection with provider-specific embeddings.
        """
        try:
            embedding_model = await self.vector_service.get_embedding_model(provider=provider)
            query_vector = await embedding_model.aget_query_embedding(query)

            candidates = await self.vector_repo.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False,
            )

            results = []
            for hit in candidates:
                payload = hit.payload or {}
                doc_id_val = payload.get("connector_document_id")

                if not doc_id_val:
                    continue

                try:
                    doc_id = UUID(doc_id_val) if isinstance(doc_id_val, str) else doc_id_val
                    content = payload.get("_node_content") or payload.get("content") or "No content available"

                    results.append(
                        SearchResult(
                            document_id=doc_id,
                            score=hit.score,
                            content=content[:100000],
                            metadata=SearchMetadata(
                                file_name=payload.get("file_name"),
                                file_path=payload.get("file_path"),
                                connector_name=payload.get("connector_name"),
                            ),
                        )
                    )
                except (ValueError, TypeError):
                    continue

            return results

        except Exception as e:
            logger.error(f"Collection vector search failed ({collection_name}): {e}")
            raise

    async def _resolve_collections(self, filters: Optional[SearchFilters]) -> list[dict]:
        """
        Determine Qdrant collections based on assistant or connector filters.
        """
        collections = []

        if filters and filters.assistant and hasattr(filters.assistant, "linked_connectors"):
            linked = filters.assistant.linked_connectors
            if not linked:
                default_provider = "gemini"
                name = await self.vector_service.get_collection_name(provider=default_provider)
                return [{"name": name, "provider": default_provider}]

            seen = set()
            for conn in linked:
                provider = conn.configuration.get("ai_provider", "gemini")
                if provider not in seen:
                    name = await self.vector_service.get_collection_name(provider=provider)
                    collections.append({"name": name, "provider": provider})
                    seen.add(provider)
            return collections

        if filters and filters.connector_id:
            connector = await self.connector_repo.get_by_id(filters.connector_id)
            if not connector:
                raise SearchExecutionError(f"Connector {filters.connector_id} not found")

            provider = connector.configuration.get("ai_provider", "gemini")
            name = await self.vector_service.get_collection_name(provider=provider)
            return [{"name": name, "provider": provider}]

        # Default
        provider = "gemini"
        name = await self.vector_service.get_collection_name(provider=provider)
        return [{"name": name, "provider": provider}]

    @property
    def strategy_name(self) -> str:
        return "VectorOnly"

    def _build_qdrant_filter(self, filters: Optional[SearchFilters]) -> Optional[models.Filter]:
        """Construct Qdrant Filter for ACL pre-filtering."""
        if not filters or not filters.user_acl:
            return None

        return models.Filter(
            must=[models.FieldCondition(key="connector_acl", match=models.MatchAny(any=filters.user_acl))]
        )
