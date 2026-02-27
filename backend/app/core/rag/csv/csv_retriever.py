"""
CSV Retrieval Service
=====================
Dedicated service for Schema-Aware Retrieval in CSV Pipelines.
Handles filter construction, scoped retrieval, and Qdrant payload hydration.
"""

import asyncio
import logging
from typing import Any, Dict, List, NamedTuple, Optional
from uuid import UUID

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores import (FilterOperator, MetadataFilter,
                                            MetadataFilters)

logger = logging.getLogger(__name__)

# Constants
KEY_YEAR_START = "year_start"
KEY_YEAR_END = "year_end"
KEY_CONNECTOR_ID = "connector_id"
KEY_MODEL = "model"


class CsvRetriever:
    """
    Service encapsulating retrieval logic for CSV RAG.

    Responsibilities (SRP):
    1. Filter Construction form Schemas.
    2. Secure Scoped Retrieval (Connector ID).
    3. Payload Hydration (Fixing projection issues).
    4. Progressive Filtering Logic.

    Security Audit (V2):
    - Multi-Tenancy: MANDATORY connector_id in all search paths.
    - Async Safety: Offloads blocking Qdrant IO to thread pool.
    """

    def __init__(self, vector_index: VectorStoreIndex, qdrant_client: Any, collection_name: str):
        self.vector_index = vector_index
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name

    async def search(
        self, query: str, filters: Dict[str, Any], connector_id: UUID, top_k: int = 10
    ) -> List[NodeWithScore]:
        """
        Performs a scoped search with mandatory connector_id filter.
        """
        try:
            # 1. Build Scoped Filters (P0 Security)
            meta_filters = self._build_scoped_filters(filters, connector_id)

            # 2. Execute Retrieval
            nodes = await self._execute_retrieval(query, meta_filters, top_k)

            # 3. Auto-Hydrate missing metadata
            await self._hydrate_nodes_payload(nodes)

            return nodes

        except Exception as e:
            logger.error(f"❌ CSV Retrieval Service Search Failed: {e}", exc_info=True)
            raise

    async def suggest(
        self,
        query: str,
        extracted_filters: Dict[str, Any],
        connector_id: UUID,  # P0: Added mandatory scope
        top_k: int = 10,
    ) -> Optional[List[NodeWithScore]]:
        """
        Runs progressive filtering to suggestion check.
        Requires tenant isolation via connector_id.
        """
        try:
            # 1. Build Scoped Filters (P0 Security)
            meta_filters = self._build_scoped_filters(extracted_filters, connector_id)
            if not meta_filters:
                return None

            # 2. Execute Retrieval
            nodes = await self._execute_retrieval(query, meta_filters, top_k)

            # 3. Check Precision
            if self._is_precise_enough(nodes, len(nodes)):
                await self._hydrate_nodes_payload(nodes)
                return nodes

            return None

        except Exception as e:
            logger.error(f"❌ CSV Retrieval Suggestion Failed: {e}", exc_info=True)
            return None

    # --- Private Helpers ---

    async def _execute_retrieval(self, query: str, filters: List[MetadataFilter], top_k: int) -> List[NodeWithScore]:
        """Low-level retrieval execution."""
        retriever = self.vector_index.as_retriever(similarity_top_k=top_k, filters=MetadataFilters(filters=filters))
        return await retriever.aretrieve(query)

    def _build_scoped_filters(self, extracted: Dict[str, Any], connector_id: UUID) -> List[MetadataFilter]:
        """
        Constructs metadata filters and ENFORCES connector_id scope.
        """
        filters = self._build_metadata_filters(extracted)  # Base filters

        # Security: Enforce Isolation
        filters.append(MetadataFilter(key=KEY_CONNECTOR_ID, value=str(connector_id), operator=FilterOperator.EQ))
        return filters

    def _build_metadata_filters(self, extracted: Dict[str, Any]) -> List[MetadataFilter]:
        """Converts dictionary of filters into strict MetadataFilter objects."""
        filters = []
        added_year = False

        for key, value in extracted.items():
            str_val = str(value).strip()

            # 1. Handle Year Logic (Range Filter)
            if "year" in key.lower() and not added_year:
                try:
                    val = int(value)
                    filters.extend(
                        [
                            MetadataFilter(key=KEY_YEAR_START, value=val, operator=FilterOperator.LTE),
                            MetadataFilter(key=KEY_YEAR_END, value=val, operator=FilterOperator.GTE),
                        ]
                    )
                    added_year = True
                except ValueError:
                    logger.warning(f"Invalid year filter value: {value}")
                continue

            # 2. Handle Exact Keys
            if len(str_val) >= 2 and "," not in str_val:
                filters.append(MetadataFilter(key=key, value=str_val, operator=FilterOperator.EQ))

        return filters

    async def _hydrate_nodes_payload(self, nodes: List[NodeWithScore]) -> None:
        """
        Hydrates node payloads from Qdrant if metadata is missing.
        P0: Uses run_in_executor to prevent blocking the Event Loop on sync Qdrant calls.
        """
        if not nodes:
            return

        # Optimization: Check if first node is already rich
        if nodes[0].node.metadata and len(nodes[0].node.metadata) > 2:
            return

        try:
            ids = [n.node.node_id for n in nodes]

            # P0: Offload blocking IO to thread pool
            loop = asyncio.get_running_loop()
            points = await loop.run_in_executor(
                None,
                lambda: self.qdrant_client.retrieve(collection_name=self.collection_name, ids=ids, with_payload=True),
            )

            # Map payloads
            payload_map = {str(p.id): p.payload for p in points}

            for n in nodes:
                payload = payload_map.get(str(n.node.node_id))
                if payload:
                    n.node.metadata.update(payload)

        except Exception as e:
            logger.error(f"Payload hydration failed: {e}")

    def _is_precise_enough(self, nodes: List[NodeWithScore], count: int) -> bool:
        """Determines if the result set is focused enough."""
        if count == 0:
            return False
            
        # P0: If many results across different entities, too broad
        if count > 5:
            return False

        # If we have only 1 or 2 results, we consider it precise enough even if they differ slightly
        if count <= 2:
            return True

        # Check Variance across identifying fields
        # If we have 3-5 results, they should all refer to the same Model/Position/Type
        identifying_keys = {KEY_MODEL, "Position", "ProductType", "Note", KEY_YEAR_START}
        
        for key in identifying_keys:
            # Robust lookup: check exact, then lowercase
            unique_vals = set()
            for n in nodes:
                meta = n.node.metadata or {}
                # Try finding the key in a case-insensitive way if not direct
                val = meta.get(key)
                if val is None:
                    # Search keys for a case-insensitive match
                    for m_key in meta.keys():
                        if m_key.lower() == key.lower():
                            val = meta[m_key]
                            break
                
                unique_vals.add(str(val if val is not None else "unknown"))

            if len(unique_vals) > 1:
                # If even ONE identifying field varies across results, it's ambiguous
                logger.info(f"Ambiguity detected: {key} varies across {len(unique_vals)} values")
                return False
            
        return True
