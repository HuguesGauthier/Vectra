import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.exceptions import EntityNotFound, TechnicalError
from app.core.security import get_current_user
from app.models.user import User
from app.services.file_service import FileService, get_file_service

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stream/{document_id}")
async def stream_file(
    document_id: UUID,
    file_service: Annotated[FileService, Depends(get_file_service)],
    # Note: Audio elements often struggle with Auth headers.
    # Ideally use a pre-signed URL or Cookie auth.
    # For this strict refactor, we require auth. Frontend must attach token.
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """
    Stream a file by its ID.

    Supports HTTP Range requests for audio/video seeking.

    Args:
        document_id: The unique identifier of the document to stream.
        file_service: Service for handling file operations.
        current_user: The currently authenticated user.

    Returns:
        FileResponse: A response object that streams the file content.

    Raises:
        EntityNotFound: If the file or document is not found.
        TechnicalError: If there is an unexpected error during streaming.
    """
    try:
        stream_info = await file_service.get_file_for_streaming(document_id)

        return FileResponse(
            path=stream_info.file_path,
            media_type=stream_info.media_type,
            filename=stream_info.file_name,
        )

    except (EntityNotFound, TechnicalError) as e:
        # FileResponse handles ranges automatically, but exceptions bubble up
        if isinstance(e, EntityNotFound):
            logger.warning(f"File not found: {e}")
        else:
            logger.error(f"Stream file error: {e}", exc_info=True)
        raise e
    except Exception as e:
        logger.error(f"Stream file unexpected error: {e}", exc_info=True)
        raise TechnicalError(message=f"Could not stream file: {e}", error_code="FILE_STREAMING_ERROR")
