"""
Vector Repository - Qdrant Data Access Object.

Handles all interactions with the Vector Database using the async client to prevent event loop blocking.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (FieldCondition, Filter, FilterSelector,
                                       MatchAny, MatchValue, PointStruct)

from app.core.exceptions import ExternalDependencyError

logger = logging.getLogger(__name__)

# Constants
UPSERT_BATCH_SIZE = 100


class VectorRepository:
    """
    Abstracts interactions with Qdrant Vector DB.

    ARCHITECT NOTE: Async I/O
    Uses AsyncQdrantClient to ensure High Concurrency in FastAPI.
    """

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def upsert_points(self, collection_name: str, points: List[PointStruct], wait: bool = False) -> None:
        """
        Upserts points into the collection.
        P0 Checks: Batch size warnings.
        """
        if not points:
            return

        try:
            if len(points) > UPSERT_BATCH_SIZE:
                logger.warning(f"Upserting large batch of {len(points)} points. Consider chunking to avoid timeouts.")

            await self.client.upsert(collection_name=collection_name, points=points, wait=wait)
            logger.debug(f"Upserted {len(points)} points to {collection_name}")

        except UnexpectedResponse as e:
            logger.error(f"Qdrant protocol error upserting to {collection_name}: {e}")
            raise ExternalDependencyError(f"Vector DB Protocol Error: {e}", service="qdrant")
        except Exception as e:
            logger.error(f"Failed to upsert points to {collection_name}: {e}")
            raise ExternalDependencyError(f"Vector DB Upsert Failed: {e}", service="qdrant")

    async def delete_by_connector_id(self, collection_name: str, connector_id: UUID) -> None:
        """Deletes all points for a connector."""
        await self._delete_by_filter(
            collection_name,
            filter_key="connector_id",
            filter_value=str(connector_id),
            context_name=f"Connector {connector_id}",
        )

    async def delete_by_document_id(self, collection_name: str, document_id: UUID) -> None:
        """Deletes all points for a document."""
        await self._delete_by_filter(
            collection_name,
            filter_key="connector_document_id",
            filter_value=str(document_id),
            context_name=f"Document {document_id}",
        )

    async def delete_by_document_ids(self, collection_name: str, document_ids: List[UUID]) -> None:
        """Deletes all points for a list of documents in batch."""
        if not document_ids:
            return

        doc_ids_str = [str(uid) for uid in document_ids]

        await self._delete_by_filter_batch(
            collection_name,
            filter_key="connector_document_id",
            filter_values=doc_ids_str,
            context_name=f"Batch Documents ({len(document_ids)})",
        )

    async def delete_by_assistant_id(self, collection_name: str, assistant_id: UUID) -> None:
        """Deletes all points (trending topics) for an assistant."""
        await self._delete_by_filter(
            collection_name,
            filter_key="assistant_id",
            filter_value=str(assistant_id),
            context_name=f"Assistant {assistant_id}",
        )

    async def _delete_by_filter(
        self, collection_name: str, filter_key: str, filter_value: str, context_name: str
    ) -> None:
        """
        DRY Helper for deletion by single specific field match.
        """
        try:
            await self.client.delete(
                collection_name=collection_name,
                points_selector=FilterSelector(
                    filter=Filter(must=[FieldCondition(key=filter_key, match=MatchValue(value=filter_value))])
                ),
                wait=True,
            )
            logger.debug(f"Deleted vectors for {context_name}")

        except Exception as e:
            if "not found" in str(e).lower():
                logger.warning(f"Collection {collection_name} not found during delete. Ignoring.")
                return

            logger.error(f"Failed to delete {context_name}: {e}")
            raise ExternalDependencyError(f"Vector DB Delete Failed: {e}", service="qdrant")

    async def _delete_by_filter_batch(
        self, collection_name: str, filter_key: str, filter_values: List[str], context_name: str
    ) -> None:
        """
        DRY Helper for deletion by MATCH ANY filter (Batch).
        """
        try:
            await self.client.delete(
                collection_name=collection_name,
                points_selector=FilterSelector(
                    filter=Filter(must=[FieldCondition(key=filter_key, match=MatchAny(any=filter_values))])
                ),
                wait=True,
            )
            logger.debug(f"Deleted vectors for {context_name}")

        except Exception as e:
            if "not found" in str(e).lower():
                logger.warning(f"Collection {collection_name} not found during delete. Ignoring.")
                return

            logger.error(f"Failed to delete {context_name}: {e}")
            raise ExternalDependencyError(f"Vector DB Delete Failed: {e}", service="qdrant")

    async def update_acl(
        self, collection_name: str, filter_key: str, filter_value: str, new_acl: Union[str, List[str]]
    ) -> None:
        """
        Updates ACL payload for points matching filter.
        """
        try:
            if isinstance(new_acl, str):
                new_acl = [new_acl]

            # Deprecated: connector_document_acl support removed.
            payload_key = "connector_acl"

            await self.client.set_payload(
                collection_name=collection_name,
                payload={payload_key: new_acl},
                points=Filter(must=[FieldCondition(key=filter_key, match=MatchValue(value=str(filter_value)))]),
            )
            logger.info(f"Updated ACL for {filter_key}={filter_value}")

        except Exception as e:
            logger.error(f"Failed to update ACL: {e}")
            raise ExternalDependencyError(f"Vector DB ACL Update Failed: {e}", service="qdrant")

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        query_filter: Optional[models.Filter] = None,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> List[Any]:
        """
        Execute similarity search using query_points (Unified API).
        """
        try:
            result = await self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,  # Enforce ACLs here
                with_payload=with_payload,
                with_vectors=with_vectors,
            )
            if hasattr(result, "points"):
                return result.points
            return result

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ExternalDependencyError(f"Vector Search Failed: {e}", service="qdrant")

    async def count_by_document_id(self, collection_name: str, document_id: UUID) -> int:
        """Counts points for a specific document."""
        try:
            result = await self.client.count(
                collection_name=collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="connector_document_id", match=models.MatchValue(value=str(document_id))
                        )
                    ]
                ),
            )
            return result.count
        except Exception as e:
            logger.error(f"Failed to count vectors for document {document_id}: {e}")
            # Non-blocking error, return 0 is safer than crashing flow
            return 0
