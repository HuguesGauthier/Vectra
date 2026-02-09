from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import EntityNotFound, TechnicalError
from app.schemas.files import FileStreamingInfo
from app.services.file_service import FileService


@pytest.fixture
def mock_document_repo():
    return AsyncMock()


@pytest.fixture
def file_service(mock_document_repo):
    return FileService(mock_document_repo)


@pytest.mark.asyncio
async def test_get_file_for_streaming_success(file_service, mock_document_repo):
    # Setup
    doc_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/test.pdf"
    mock_doc.file_name = "test.pdf"
    mock_document_repo.get_by_id.return_value = mock_doc

    with patch("asyncio.to_thread", AsyncMock(return_value=True)):
        # Execute
        result = await file_service.get_file_for_streaming(doc_id)

        # Verify
        assert isinstance(result, FileStreamingInfo)
        assert result.file_path == "/tmp/test.pdf"
        assert result.file_name == "test.pdf"
        assert result.media_type == "application/pdf"
        mock_document_repo.get_by_id.assert_called_once_with(doc_id)


@pytest.mark.asyncio
async def test_get_file_for_streaming_not_found(file_service, mock_document_repo):
    # Setup
    doc_id = uuid4()
    mock_document_repo.get_by_id.return_value = None

    # Execute & Verify
    with pytest.raises(EntityNotFound):
        await file_service.get_file_for_streaming(doc_id)


@pytest.mark.asyncio
async def test_get_file_for_streaming_file_missing_on_disk(file_service, mock_document_repo):
    # Setup
    doc_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.file_path = "/tmp/missing.pdf"
    mock_document_repo.get_by_id.return_value = mock_doc

    with patch("asyncio.to_thread", AsyncMock(return_value=False)):
        # Execute & Verify
        with pytest.raises(EntityNotFound) as excinfo:
            await file_service.get_file_for_streaming(doc_id)
        assert "File resource missing" in str(excinfo.value)
