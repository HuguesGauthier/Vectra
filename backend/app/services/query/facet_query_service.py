"""
Facet Query Service
===================
Service for retrieving distinct facet values from Qdrant vector store.
Used by AmbiguityGuardAgent to suggest filter options to users.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, Record

logger = logging.getLogger(__name__)

# Constants
DEFAULT_LIMIT_FACET = 50
BATCH_SIZE = 100
KEY_CONNECTOR_ID = "connector_id"


class FacetQueryService:
    """
    Queries Qdrant for distinct values of filterable fields.

    Responsibilities (SRP):
    1. Filter Construction (Dict -> Qdrant Filter).
    2. Scrolling & Extraction (Async IO offloading).
    3. Hierarchy Logic (Recursive drill-down).

    Security Audit (V2):
    - Multi-Tenancy: MANDATORY connector_id in all search paths.
    - Async Safety: IO offloaded to Executor.
    """

    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client

    async def get_facet_values(
        self,
        collection_name: str,
        facet_field: str,
        connector_id: UUID,  # P0: Mandatory Scope
        partial_filters: Optional[Dict[str, str]] = None,
        limit: int = DEFAULT_LIMIT_FACET,
    ) -> List[str]:
        """
        Get distinct values for a facet field safely (Non-blocking).
        """
        try:
            # 1. Build Scoped Filter
            point_filter = self._build_scoped_qdrant_filter(partial_filters, connector_id)

            # 2. Scroll & Extract (Offloaded IO)
            distinct_values = await self._scroll_distinct_values(collection_name, facet_field, point_filter, limit)

            # 3. Sort & Return
            result = sorted(list(distinct_values))[:limit]
            logger.info(f"✅ Facet query: {facet_field} -> {len(result)} values found.")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to get facet values for {facet_field}: {e}", exc_info=True)
            return []

    async def get_hierarchical_facets(
        self,
        collection_name: str,
        facet_hierarchy: List[str],
        connector_id: UUID,  # P0: Mandatory Scope
        partial_filters: Optional[Dict[str, str]] = None,
        limit_per_level: int = 20,
    ) -> Dict[str, List[str]]:
        """
        Get facet values for multiple levels of hierarchy.
        """
        result = {}
        current_filters = partial_filters.copy() if partial_filters else {}

        for facet_field in facet_hierarchy:
            # Optimization: Skip if already narrowed
            if facet_field in current_filters:
                result[facet_field] = [current_filters[facet_field]]
                continue

            values = await self.get_facet_values(
                collection_name=collection_name,
                facet_field=facet_field,
                connector_id=connector_id,
                partial_filters=current_filters.copy(),
                limit=limit_per_level,
            )

            result[facet_field] = values

            # Auto-Narrowing: If only one value exists, assume it for the next level
            if len(values) == 1:
                current_filters[facet_field] = values[0]

        return result

    # --- Private Helpers: Logic Atomization ---

    def _build_scoped_qdrant_filter(self, filters: Optional[Dict[str, str]], connector_id: UUID) -> Filter:
        """Converts simple dict to Qdrant Filter object AND enforces scope."""
        conditions = []

        # Add User Filters
        if filters:
            conditions.extend([FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()])

        # Add Security Scope (P0)
        conditions.append(FieldCondition(key=KEY_CONNECTOR_ID, match=MatchValue(value=str(connector_id))))

        return Filter(must=conditions)

    async def _scroll_distinct_values(
        self, collection: str, field: str, q_filter: Optional[Filter], limit: int
    ) -> Set[str]:
        """
        Scrolls through Qdrant records to find distinct values.
        Offloads blocking IO to thread Executor (Event Loop safe).
        """
        distinct_values = set()
        offset = None

        loop = asyncio.get_running_loop()

        while len(distinct_values) < limit:
            # P0: Run Sync Client IO in Thread
            records, next_offset = await loop.run_in_executor(
                None,
                lambda: self.client.scroll(
                    collection_name=collection,
                    scroll_filter=q_filter,
                    limit=BATCH_SIZE,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                ),
            )

            # Extract
            self._extract_values_from_records(records, field, distinct_values)

            # Break Condition
            if next_offset is None or len(distinct_values) >= limit:
                break

            offset = next_offset

        return distinct_values

    def _extract_values_from_records(self, records: List[Record], field: str, target_set: Set[str]) -> None:
        """Helper to parse payload safely."""
        for record in records:
            if not record.payload:
                continue

            value = record.payload.get(field)
            if value:
                target_set.add(str(value))  # Normalize to string
