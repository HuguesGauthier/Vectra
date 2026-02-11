import asyncio
import logging
from typing import Annotated, Any, List, Optional
from uuid import UUID

from pydantic import Field
from qdrant_client.http import models

from app.models.enums import ConnectorStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
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
CANDIDATE_MULTIPLIER = 2  # Fetch 2x candidates for post-filtering
DEFAULT_COLLECTION = "vectra_vectors"  # Fallback


class HybridStrategy(SearchStrategy):
    """
    Hybrid search combining vector similarity and SQL metadata filtering.

    ARCHITECT NOTE: Pipeline Execution
    1. Resolve Collection (via Connector)
    2. Vectorize Query (via VectorService)
    3. Retrieval (Qdrant)
    4. Metadata Filtering (PostgreSQL) - Critical for status enforcement
    5. Fusion/Ranking
    """

    def __init__(
        self,
        vector_repo: VectorRepository,
        document_repo: DocumentRepository,
        connector_repo: ConnectorRepository,
        vector_service: VectorService,
    ):
        """
        Initialize with all required dependencies for hybrid RAG.
        """
        super().__init__()
        self.vector_repo = vector_repo
        self.document_repo = document_repo
        self.connector_repo = connector_repo
        self.vector_service = vector_service

    async def search(
        self,
        query: Annotated[str, Field(min_length=1, max_length=MAX_QUERY_LENGTH)],
        top_k: Annotated[int, Field(ge=1, le=MAX_TOP_K)] = DEFAULT_TOP_K,
        filters: Optional[SearchFilters] = None,
    ) -> list[SearchResult]:
        """
        Execute hybrid search with multi-collection support and SQL post-filtering.
        """
        self._log_search_start(query, top_k)

        try:
            # 1. Resolve Collections
            collections_info = await self._resolve_collections(filters)

            if not collections_info:
                logger.warning("No collections resolved for search")
                self._log_search_complete(0, 0)
                return []

            # 2. Build Pre-Filter (ACLs only for Qdrant)
            qdrant_filter = self._build_qdrant_filter(filters)

            # 3. Query all collections in parallel
            search_tasks = []
            for coll_info in collections_info:
                task = self._search_single_collection(
                    collection_name=coll_info["name"],
                    provider=coll_info["provider"],
                    query=query,
                    top_k=top_k * CANDIDATE_MULTIPLIER,
                    qdrant_filter=qdrant_filter,
                )
                search_tasks.append(task)

            all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # 4. Merge and Initial Filter
            merged_results = []
            for idx, result in enumerate(all_results):
                if isinstance(result, Exception):
                    logger.error(f"Error searching collection {collections_info[idx]['name']}: {result}")
                    continue
                merged_results.extend(result)

            if not merged_results:
                self._log_search_complete(0, 0)
                return []

            # 5. SQL Post-Filtering (P0 Security: Enforce current DB status)
            effective_filters = filters or SearchFilters()
            merged_results = await self._apply_sql_filters(merged_results, effective_filters)

            # 6. Sort and Limit
            merged_results.sort(key=lambda x: x.score, reverse=True)
            final_results = merged_results[:top_k]

            self._log_search_complete(len(final_results), 0)
            return final_results

        except Exception as e:
            self._log_search_error(e)
            if isinstance(e, SearchExecutionError):
                raise
            raise SearchExecutionError(f"Hybrid search pipeline failed: {e}") from e

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
            logger.error(f"Collection search failed ({collection_name}): {e}")
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

    async def _apply_sql_filters(self, results: list[SearchResult], filters: SearchFilters) -> list[SearchResult]:
        """
        Validate vector candidates against current database state.
        Ensures status and permissions are enforced via PostgreSQL source of truth.
        """
        if not results:
            return []

        # 1. Batch fetch from SQL (P1: Optimization)
        doc_ids = [r.document_id for r in results]
        db_docs = await self.document_repo.get_by_ids(doc_ids)

        # Map for O(1) lookup
        doc_map = {doc.id: doc for doc in db_docs}

        valid_results = []
        for res in results:
            doc = doc_map.get(res.document_id)
            if not doc:
                continue

            # 2. Status Enforcement
            # Default to INDEXED if status check is desired but status filter not explicitly set,
            # but usually we only filter if filters.status is present.
            if filters.status and doc.status != filters.status:
                continue

            # P1 Security: Ensure we only return indexed content by default in prod
            if doc.status not in ["INDEXED"]:
                logger.debug(f"Skipping doc {doc.id} with status {doc.status}")
                continue

            valid_results.append(res)

        return valid_results

    @property
    def strategy_name(self) -> str:
        return "Hybrid"

    def _build_qdrant_filter(self, filters: Optional[SearchFilters]) -> Optional[models.Filter]:
        """Construct Qdrant Filter for ACL pre-filtering."""
        if not filters or not filters.user_acl:
            return None

        return models.Filter(
            must=[models.FieldCondition(key="connector_acl", match=models.MatchAny(any=filters.user_acl))]
        )
