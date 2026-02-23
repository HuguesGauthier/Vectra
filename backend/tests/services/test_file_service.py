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
    mock_doc.file_path = "test.pdf"
    mock_doc.file_name = "test.pdf"
    mock_doc.connector_id = uuid4()
    mock_document_repo.get_by_id.return_value = mock_doc

    mock_connector = MagicMock()
    mock_connector.connector_type = "file"
    mock_connector.configuration = {"path": "/tmp/test.pdf"}

    with patch("app.services.file_service.ConnectorRepository") as mock_crepo_cls, \
         patch("asyncio.to_thread", AsyncMock(return_value=True)):
        
        mock_crepo = mock_crepo_cls.return_value
        mock_crepo.get_by_id = AsyncMock(return_value=mock_connector)
        
        # Execute
        result = await file_service.get_file_for_streaming(doc_id)

        # Verify
        assert isinstance(result, FileStreamingInfo)
        assert result.file_path == "/tmp/test.pdf"
        assert result.file_name == "test.pdf"
        assert result.media_type == "application/pdf"


@pytest.mark.asyncio
async def test_get_file_for_streaming_not_found(file_service, mock_document_repo):
    # Setup
    doc_id = uuid4()
    mock_document_repo.get_by_id.return_value = None

    # Execute & Verify
    with pytest.raises(EntityNotFound):
        await file_service.get_file_for_streaming(doc_id)


@pytest.mark.asyncio
async def test_get_file_for_streaming_connector_not_found(file_service, mock_document_repo):
    """Test when document exists but connector is missing."""
    doc_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.connector_id = uuid4()
    mock_document_repo.get_by_id.return_value = mock_doc

    with patch("app.services.file_service.ConnectorRepository") as mock_crepo_cls:
        mock_crepo = mock_crepo_cls.return_value
        mock_crepo.get_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(EntityNotFound) as excinfo:
            await file_service.get_file_for_streaming(doc_id)
        assert "Connector" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_file_for_streaming_file_missing_on_disk(file_service, mock_document_repo):
    # Setup
    doc_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.file_path = "missing.pdf"
    mock_doc.connector_id = uuid4()
    mock_document_repo.get_by_id.return_value = mock_doc

    mock_connector = MagicMock()
    mock_connector.connector_type = "file"
    mock_connector.configuration = {"path": "/tmp/missing.pdf"}

    with patch("app.services.file_service.ConnectorRepository") as mock_crepo_cls, \
         patch("asyncio.to_thread", AsyncMock(return_value=False)):
        
        mock_crepo = mock_crepo_cls.return_value
        mock_crepo.get_by_id = AsyncMock(return_value=mock_connector)

        # Execute & Verify
        with pytest.raises(EntityNotFound) as excinfo:
            await file_service.get_file_for_streaming(doc_id)
        assert "File resource missing" in str(excinfo.value)
