"""
This module provides API endpoints for streaming audio files.
"""

import logging
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from app.api.v1.endpoints.chat import get_optional_user
from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.models.user import User
from app.schemas.files import FileStreamingInfo
from app.services.file_service import FileService, get_file_service

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stream/{document_id}")
async def stream_audio(
    document_id: UUID,
    request: Request,
    file_service: Annotated[FileService, Depends(get_file_service)],
    user: Annotated[Optional[User], Depends(get_optional_user)],
) -> FileResponse:
    """
    Streams an audio file from the server.

    This endpoint retrieves file information for a given document ID and returns
    a FileResponse to stream the audio file. It delegates Range handling to
    Starlette's FileResponse implementation.

    Args:
        document_id: The unique identifier of the audio document to stream.
        request: The FastAPI Request object.
        file_service: The file service for handling file operations.
        user: The optionally authenticated user making the request.

    Returns:
        FileResponse: A response object that streams the requested audio file.

    Raises:
        EntityNotFound: If the document or its associated connector is not found.
        FunctionalError: If there is a functional issue with the request.
        TechnicalError: If an unexpected error occurs during streaming.
    """
    try:
        # P2: Strict Typing with Pydantic model
        stream_info: FileStreamingInfo = await file_service.get_file_for_streaming(document_id, current_user=user)

        # Access log audit could go here if needed
        # if user: logger.debug(f"Streaming {document_id} for {user.email}")

        return FileResponse(
            path=stream_info.file_path,
            media_type=stream_info.media_type,
            filename=stream_info.file_name,
            content_disposition_type="inline",
        )

    except (EntityNotFound, FunctionalError):
        # Already logged or handled at service level if needed
        raise
    except Exception as e:
        logger.error(f"Audio stream failed for {document_id}: {str(e)}", exc_info=True)
        raise TechnicalError(f"Audio stream failed: {str(e)}")
