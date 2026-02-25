import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.services.document_service import DocumentService, get_document_service
from app.services.system_service import SystemService, get_system_service

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Response Models ---


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class FilePathResponse(BaseModel):
    """File path response."""

    path: str


class OpenFileRequest(BaseModel):
    """
    Request model for opening a file.

    Attributes:
        document_id: The ID of the document to open.
    """

    document_id: str


@router.post("/open-file", response_model=MessageResponse)
async def open_file_external(
    request: OpenFileRequest,
    service: Annotated[SystemService, Depends(get_system_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """
    Open a file using the system's default application based on document ID.

    Reconstructs the full path using connector configuration.
    Basic auth required.

    Args:
        request: The request body containing document_id.
        service: The system service instance.
        current_user: The currently authenticated user.

    Returns:
        A dictionary containing the status of the operation.

    Raises:
        Exception: If there's an error opening the file.
    """
    try:
        success = await service.open_file_by_document_id(request.document_id)
        return {"message": "File opened", "success": success}
    except Exception as e:
        logger.error(
            f"❌ FAIL | open_file_external | DocumentID: {request.document_id} | Error: {str(e)}",
            exc_info=True,
        )
        raise e


@router.post("/upload", response_model=FilePathResponse)
async def upload_file(
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    file: UploadFile = File(...),
) -> FilePathResponse:
    """
    Upload a file to the temporary area.

    Admin only.

    Args:
        service: The document service instance.
        current_admin: The currently authenticated admin user.
        file: The file to be uploaded.

    Returns:
        A dictionary containing the path of the uploaded file.

    Raises:
        Exception: If there's an error during file upload.
    """
    try:
        # Delegate to Service
        file_path = await service.upload_file(file)
        return {"path": file_path}
    except Exception as e:
        logger.error(f"❌ FAIL | upload_file | Error: {str(e)}", exc_info=True)
        raise e


class DeleteTempFileRequest(BaseModel):
    """
    Request model for deleting a temporary file.

    Attributes:
        path: The path of the temporary file to delete.
    """

    path: str


@router.delete("/temp-file", response_model=MessageResponse)
async def delete_temp_file(
    request: DeleteTempFileRequest,
    service: Annotated[DocumentService, Depends(get_document_service)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> MessageResponse:
    """
    Delete a temporary uploaded file.

    Admin only.
    Used when user cancels connector creation after uploading.

    Args:
        request: The request body containing the file path.
        service: The document service instance.
        current_admin: The currently authenticated admin user.

    Returns:
        A dictionary containing a success message.

    Raises:
        Exception: If there's an error during file deletion.
    """
    try:
        await service.delete_temp_file(request.path)
        return {"message": "File deleted successfully"}
    except Exception as e:
        logger.error(
            f"❌ FAIL | delete_temp_file | Path: {request.path} | Error: {str(e)}",
            exc_info=True,
        )
        raise e
