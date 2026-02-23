import os
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.connector_document import ConnectorDocument

logger = logging.getLogger(__name__)


class SourceService:
    """
    Shared service for processing and formatting retrieval sources.
    Handles metadata cleanup, file path recovery from DB, and normalization.
    """

    @staticmethod
    def _sanitize_data(data: Any) -> Any:
        """Recursively convert Decimal to float and handle other JSON-unfriendly types."""
        if isinstance(data, Decimal):
            return float(data)
        if isinstance(data, dict):
            return {k: SourceService._sanitize_data(v) for k, v in data.items()}
        if isinstance(data, list):
            return [SourceService._sanitize_data(i) for i in data]
        if isinstance(data, UUID):
            return str(data)
        return data

    @staticmethod
    async def process_sources(nodes: List[Any], db: AsyncSession) -> List[Dict]:
        """
        Securely process sources with DB fallback for file_path.

        Args:
            nodes: List of LlamaIndex NodeWithScore objects
            db: Async database session

        Returns:
            List of normalized source dictionaries ready for frontend
        """
        sources = []

        # Collect document IDs that need file_path lookup
        missing_paths = {}
        for node in nodes:
            meta = node.node.metadata or {}
            doc_id_val = meta.get("connector_document_id")
            if not meta.get("file_path") and doc_id_val:
                try:
                    # Validate UUID format before adding to batch fetch
                    if isinstance(doc_id_val, str):
                        UUID(doc_id_val)
                    missing_paths[str(doc_id_val)] = None
                except (ValueError, AttributeError):
                    logger.debug(f"Invalid connector_document_id format: {doc_id_val}")
                    pass

        # Batch fetch file paths from DB
        if missing_paths:
            try:
                doc_ids = [UUID(doc_id_str) for doc_id_str in missing_paths.keys()]
                result = await db.execute(
                    select(ConnectorDocument.id, ConnectorDocument.file_path, ConnectorDocument.file_name).where(
                        ConnectorDocument.id.in_(doc_ids)
                    )
                )
                rows = result.all()
                for row in rows:
                    missing_paths[str(row.id)] = {"file_path": row.file_path, "file_name": row.file_name}
            except Exception as e:
                logger.error(f"Failed to fetch file_paths from DB: {e}")

        for node in nodes:
            # Handle different node types (TextNode vs others)
            if hasattr(node.node, "get_content"):
                txt = node.node.get_content()
            else:
                txt = str(node.node.text) if hasattr(node.node, "text") else ""

            meta = node.node.metadata or {}

            # Safe JSON parse attempt (Legacy format handling)
            if txt and txt.strip().startswith("{"):
                try:
                    import json

                    p = json.loads(txt)
                    if isinstance(p, dict):
                        txt = p.get("text", p.get("content", txt))
                        if "metadata" in p:
                            meta.update(p["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass

            if "page_number" in meta and "page_label" not in meta:
                meta["page_label"] = str(meta["page_number"])

            # Extract file path and name for frontend compatibility
            file_path = meta.get("file_path")
            file_name = meta.get("file_name") or meta.get("filename") or meta.get("name", "Unknown")

            # Fallback: fetch from DB if not in Qdrant metadata
            if not file_path and doc_id_val:
                doc_data = missing_paths.get(str(doc_id_val))
                if doc_data:
                    file_path = doc_data["file_path"]
                    meta["file_path"] = file_path
                    if not file_name or file_name == "Unknown":
                        file_name = doc_data["file_name"]
                        meta["file_name"] = file_name

            # Safe fallback for file_name: derivation from path if missing
            if (not file_name or file_name == "Unknown") and file_path:
                file_name = os.path.basename(file_path)
                meta["file_name"] = file_name

            # Determine file type from extension if available
            file_type = "txt"  # default
            if file_path:
                _, ext = os.path.splitext(file_path)
                ext = ext.lstrip(".").lower()
                if ext == "pdf":
                    file_type = "pdf"
                elif ext in ["docx", "doc"]:
                    file_type = "docx"
                elif ext in ["mp3", "wav", "m4a", "aac", "flac"]:
                    file_type = "audio"

            sources.append(
                {
                    "id": node.node.node_id,
                    "name": file_name,
                    "type": file_type,
                    "text": txt,
                    "metadata": meta,  # Contains connector_document_id for file opening
                    "score": float(node.score) if node.score is not None else 0.0,
                }
            )

        return SourceService._sanitize_data(sources)
