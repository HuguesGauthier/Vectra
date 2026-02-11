"""
Connectors API Endpoints.

This module provides the API endpoints for managing connectors and their associated documents.
Connectors are used to ingest data from various sources (SQL, files, etc.).
"""

import asyncio
import logging
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.connection_manager import manager
from app.core.security import get_current_admin
from app.models.enums import DocStatus
from app.models.user import User
from app.schemas.connector import ConnectorCreate, ConnectorResponse, ConnectorUpdate
from app.schemas.documents import ConnectorDocumentCreate, ConnectorDocumentResponse, ConnectorDocumentUpdate
from app.services.connector_service import ConnectorService, get_connector_service
from app.services.document_service import DocumentService, get_document_service
from app.services.sql_discovery_service import get_sql_discovery_service

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Connectors ---


@router.post("/test-connection")
async def test_connection(
    payload: Dict[str, Any],
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    sql_discovery_service: Annotated[Any, Depends(get_sql_discovery_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, Any]:
    """
    Test a connector connection (primarily for SQL).

    Args:
        payload: Dictionary containing connector_type and configuration.
        service: The connector service instance.
        sql_discovery_service: The SQL discovery service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, Any]: A success status and message.
    """
    connector_type = payload.get("connector_type")
    configuration = payload.get("configuration")

    if not connector_type or not configuration:
        return {"success": False, "message": "Missing connector_type or configuration"}

    if connector_type in ["sql", "vanna_sql"]:
        try:
            await sql_discovery_service.test_connection(configuration)
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            logger.error("Connection test failed for %s: %s", connector_type, e)
            return {"success": False, "message": str(e)}

    # Add other types if needed
    return {"success": False, "message": f"Connection test not implemented for {connector_type}"}


@router.get("/", response_model=List[ConnectorResponse])
async def get_connectors(
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> List[ConnectorResponse]:
    """
    List all connectors.

    Args:
        service: The connector service instance.
        current_user: The currently authenticated admin user.

    Returns:
        List[ConnectorResponse]: A list of all connectors.
    """
    return await service.get_connectors()


@router.post("/", response_model=ConnectorResponse)
async def create_connector(
    connector: ConnectorCreate,
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> ConnectorResponse:
    """
    Create a new connector.

    Args:
        connector: The connector creation data.
        service: The connector service instance.
        current_user: The currently authenticated admin user.

    Returns:
        ConnectorResponse: The created connector.
    """
    return await service.create_connector(connector)


@router.put("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: UUID,
    connector: ConnectorUpdate,
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> ConnectorResponse:
    """
    Update an existing connector.

    Args:
        connector_id: The ID of the connector to update.
        connector: The connector update data.
        service: The connector service instance.
        current_user: The currently authenticated admin user.

    Returns:
        ConnectorResponse: The updated connector.
    """
    return await service.update_connector(connector_id, connector)


@router.delete("/{connector_id}")
async def delete_connector(
    connector_id: UUID,
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, str]:
    """
    Delete a connector and its resources.

    Args:
        connector_id: The ID of the connector to delete.
        service: The connector service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, str]: A success message.
    """
    await service.delete_connector(connector_id)
    return {"message": "Connector deleted successfully"}


@router.post("/{connector_id}/sync", response_model=ConnectorResponse)
async def sync_connector(
    connector_id: UUID,
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
    force: bool = False,
) -> ConnectorResponse:
    """
    Trigger manual synchronization for a connector.

    Args:
        connector_id: The ID of the connector to sync.
        service: The connector service instance.
        current_user: The currently authenticated admin user.
        force: Whether to force synchronization.

    Returns:
        ConnectorResponse: The connector being synced.
    """
    connector = await service.trigger_sync(connector_id, force)
    await manager.emit_trigger_connector_sync(str(connector_id))
    return connector


@router.post("/{connector_id}/scan-files/", response_model=ConnectorResponse)
@router.post("/{connector_id}/scan-files", response_model=ConnectorResponse)
async def scan_connector_files(
    connector_id: UUID,
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> ConnectorResponse:
    """
    Trigger manual file scan for a folder connector.

    Args:
        connector_id: The ID of the connector to scan.
        service: The connector service instance.
        current_user: The currently authenticated admin user.

    Returns:
        ConnectorResponse: The connector being scanned.
    """
    return await service.scan_connector(connector_id)


@router.post("/{connector_id}/stop", response_model=ConnectorResponse)
async def stop_connector(
    connector_id: UUID,
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> ConnectorResponse:
    """
    Request to stop a running connector sync.

    Args:
        connector_id: The ID of the connector to stop.
        service: The connector service instance.
        current_user: The currently authenticated admin user.

    Returns:
        ConnectorResponse: The connector being stopped.
    """
    return await service.stop_connector(connector_id)


@router.post("/{connector_id}/train")
async def train_vanna_connector(
    connector_id: UUID,
    payload: Dict[str, Any],
    service: Annotated[ConnectorService, Depends(get_connector_service)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, Any]:
    """
    Train Vanna AI on specific documents (tables/views) for vanna_sql connector.

    Args:
        connector_id: The ID of the connector.
        payload: Dictionary containing `document_ids` list.
        service: The connector service instance.
        document_service: The document service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, Any]: A summary of the training results.
    """
    document_ids = payload.get("document_ids", [])
    if not document_ids:
        return {"success": False, "message": "document_ids array is required"}

    # Load connector
    connector = await service.get_connector(connector_id)
    if not connector:
        return {"success": False, "message": "Connector not found"}

    if connector.connector_type != "vanna_sql":
        return {"success": False, "message": "Training is only available for vanna_sql connectors"}

    try:
        # Initialize Vanna service (Async Factory)
        # P1: Local import to avoid missing dependency issues in some environments
        from app.services.chat.vanna_services import VannaServiceFactory

        vanna_svc = await VannaServiceFactory(service.settings_service)

        trained_count = 0
        failed_count = 0

        # Train each document
        for doc_id in document_ids:
            try:
                # Get document from repo via service
                target_uuid = UUID(doc_id) if isinstance(doc_id, str) else doc_id
                document = await document_service.document_repo.get_by_id(target_uuid)
                if not document:
                    logger.warning("Document %s not found, skipping", doc_id)
                    failed_count += 1
                    continue

                # Get DDL from file_metadata
                ddl_content = (document.file_metadata or {}).get("ddl")
                if not ddl_content:
                    logger.warning("Document %s has no DDL content, skipping", doc_id)
                    failed_count += 1
                    continue

                # Train Vanna with document's DDL content
                await asyncio.to_thread(vanna_svc.train, ddl=ddl_content)

                # Mark as trained in metadata
                meta = document.file_metadata or {}
                meta["trained"] = True
                meta["trained_at"] = datetime.utcnow().isoformat()

                # Update document
                await document_service.update_document(document.id, {"file_metadata": meta})

                trained_count += 1
                logger.info("Trained Vanna on document: %s", document.file_name)

            except Exception as doc_error:
                logger.error("Failed to train document %s: %s", doc_id, doc_error)
                failed_count += 1

        return {
            "success": True,
            "message": f"Training completed. {trained_count} documents trained, {failed_count} failed.",
            "trained_count": trained_count,
            "failed_count": failed_count,
        }
    except Exception as e:
        logger.error("Training failed: %s", e, exc_info=True)
        return {"success": False, "message": f"Training failed: {str(e)}"}


# --- Documents ---


@router.get("/{connector_id}/documents", response_model=Dict[str, Any])
async def get_connector_documents(
    connector_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
    page: int = 1,
    size: int = 20,
    status: Optional[DocStatus] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get paginated documents for a connector.

    Args:
        connector_id: The ID of the connector.
        service: The document service instance.
        current_user: The currently authenticated admin user.
        page: The page number.
        size: The page size.
        status: Filter by document status.
        search: Search term for file name or path.

    Returns:
        Dict[str, Any]: Paginated document results.
    """
    result = await service.get_connector_documents(connector_id, page, size, status, search)
    # The service already returns ConnectorDocumentResponse objects, but we ensure it here.
    result["items"] = [ConnectorDocumentResponse.model_validate(doc) for doc in result["items"]]
    return result


@router.post("/{connector_id}/documents", response_model=ConnectorDocumentResponse)
async def create_connector_document(
    connector_id: UUID,
    document: ConnectorDocumentCreate,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> ConnectorDocumentResponse:
    """
    Manually add a document to a connector.

    Args:
        connector_id: The ID of the connector.
        document: The document creation data.
        service: The document service instance.
        current_user: The currently authenticated admin user.

    Returns:
        ConnectorDocumentResponse: The created document.
    """
    return await service.create_document(connector_id, document)


@router.delete("/{connector_id}/documents/{document_id}")
async def delete_document(
    connector_id: UUID,
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, str]:
    """
    Delete a specific document.

    Args:
        connector_id: The ID of the connector.
        document_id: The ID of the document to delete.
        service: The document service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, str]: A success message.
    """
    await service.delete_document(document_id)
    return {"message": "Document deleted successfully"}


@router.put("/{connector_id}/documents/{document_id}", response_model=ConnectorDocumentResponse)
async def update_document(
    connector_id: UUID,
    document_id: UUID,
    document: ConnectorDocumentUpdate,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> ConnectorDocumentResponse:
    """
    Update a specific document.

    Args:
        connector_id: The ID of the connector.
        document_id: The ID of the document to update.
        document: The document update data.
        service: The document service instance.
        current_user: The currently authenticated admin user.

    Returns:
        ConnectorDocumentResponse: The updated document.
    """
    return await service.update_document(document_id, document)


@router.post("/{connector_id}/documents/{document_id}/stop")
async def stop_document(
    connector_id: UUID,
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, str]:
    """
    Request to stop re-sync for a single document.

    Args:
        connector_id: The ID of the connector.
        document_id: The ID of the document to stop.
        service: The document service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, str]: A success message.
    """
    await service.stop_document(document_id)
    return {"message": "Document sync stop requested"}


@router.post("/{connector_id}/documents/{document_id}/sync")
async def sync_document(
    connector_id: UUID,
    document_id: UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_user: Annotated[User, Depends(get_current_admin)],
) -> Dict[str, str]:
    """
    Trigger re-sync for a single document.

    Args:
        connector_id: The ID of the connector.
        document_id: The ID of the document to sync.
        service: The document service instance.
        current_user: The currently authenticated admin user.

    Returns:
        Dict[str, str]: A success message.
    """
    await service.sync_document(document_id)
    return {"message": "Document sync queued"}
