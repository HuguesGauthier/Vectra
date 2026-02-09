import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (DuplicateError, EntityNotFound,
                                 FunctionalError, InternalDataCorruption,
                                 TechnicalError)
from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.enums import DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.documents import (ConnectorDocumentCreate,
                                   ConnectorDocumentUpdate)
from app.services.document_service import DocumentService
from app.services.settings_service import SettingsService
from app.services.vector_service import VectorService

# --- Fixtures ---


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_doc_repo(mock_db_session):
    repo = MagicMock(spec=DocumentRepository)
    repo.db = mock_db_session
    return repo


@pytest.fixture
def mock_conn_repo(mock_db_session):
    repo = MagicMock(spec=ConnectorRepository)
    repo.db = mock_db_session
    return repo


@pytest.fixture
def mock_settings_service(mock_db_session):
    ss = MagicMock()
    ss.get_value = AsyncMock()
    return ss


@pytest.fixture
def mock_vector_service(mock_settings_service):
    vs = MagicMock()
    vs.get_collection_name = AsyncMock(return_value="test_collection")
    vs.get_async_qdrant_client = MagicMock()
    return vs


@pytest.fixture
def document_service(mock_doc_repo, mock_conn_repo, mock_vector_service, mock_settings_service):
    return DocumentService(
        document_repo=mock_doc_repo,
        connector_repo=mock_conn_repo,
        vector_service=mock_vector_service,
        settings_service=mock_settings_service,
    )


@pytest.fixture
def mock_ws_manager():
    with patch("app.services.document_service.manager") as manager_mock:
        manager_mock.emit_document_deleted = AsyncMock()
        manager_mock.emit_document_updated = AsyncMock()
        manager_mock.emit_document_created = AsyncMock()
        manager_mock.emit_trigger_document_sync = AsyncMock()
        manager_mock.emit_document_update = AsyncMock()
        manager_mock.emit_connector_updated = AsyncMock()
        yield manager_mock


def mock_blocking_io(func, *args, **kwargs):
    if func == os.makedirs:
        return
    if func == os.path.exists:
        return True
    if func == os.remove:
        return
    return None


# --- Tests ---


@pytest.mark.asyncio
async def test_upload_file_async_nominal(document_service):
    """Test async streaming upload."""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.txt"
    mock_file.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])  # Stream content

    # Mock aiofiles
    mock_f = AsyncMock()
    mock_f.write = AsyncMock()

    # Context Manager Mock for aiofiles.open
    mock_aio_open = MagicMock()
    mock_aio_open.__aenter__.return_value = mock_f
    mock_aio_open.__aexit__.return_value = None

    with (
        patch("aiofiles.open", return_value=mock_aio_open) as m_open,
        patch.object(document_service, "_run_blocking_io") as mock_run,
    ):

        path = await document_service.upload_file(mock_file)

        assert "temp_uploads" in path
        assert "test.txt" in path
        assert mock_file.read.call_count == 3
        mock_f.write.assert_awaited()
        mock_run.assert_awaited()  # makedirs


@pytest.mark.asyncio
async def test_delete_document_background_tasks(document_service, mock_doc_repo, mock_conn_repo, mock_ws_manager):
    """Test deletion spawns background tasks."""
    doc_id = uuid4()
    cid = uuid4()
    c = Connector(
        id=cid, name="Test", connector_type="local_file", configuration={"ai_provider": "gemini"}, total_docs_count=5
    )
    doc = ConnectorDocument(id=doc_id, connector_id=c.id, file_path="/tmp/f.txt")

    mock_doc_repo.get_by_id = AsyncMock(return_value=doc)
    mock_conn_repo.get_by_id = AsyncMock(return_value=c)
    mock_doc_repo.delete = AsyncMock()
    mock_conn_repo.update = AsyncMock()

    with patch("asyncio.create_task") as mock_task:
        await document_service.delete_document(doc_id)

        # Should verify we tried to spawn tasks (Vector delete + File delete)
        assert mock_task.call_count >= 1
        mock_doc_repo.delete.assert_called_once_with(doc_id)

        # Count update check
        mock_conn_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_create_document_nominal(document_service, mock_conn_repo, mock_doc_repo, mock_ws_manager):
    """Test standard flow."""
    cid = uuid4()
    c = Connector(id=cid, name="Test", connector_type="local_file", schedule_type="manual", total_docs_count=0)
    mock_conn_repo.get_by_id = AsyncMock(return_value=c)

    doc_data = ConnectorDocumentCreate(file_name="test.txt", file_path="/p/t.txt")
    doc_dict = doc_data.model_dump()
    if "configuration" not in doc_dict or doc_dict["configuration"] is None:
        doc_dict["configuration"] = {}
    mock_doc_repo.create = AsyncMock(return_value=ConnectorDocument(id=uuid4(), connector_id=cid, **doc_dict))

    await document_service.create_document(cid, doc_data)
    mock_doc_repo.create.assert_called_once()
    mock_conn_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_document_acl_background(document_service, mock_doc_repo, mock_ws_manager):
    """Test ACL update spawns background task."""
    doc_id = uuid4()
    doc_before = ConnectorDocument(
        id=doc_id,
        connector_id=uuid4(),
        file_path="/test/path.txt",
        file_name="path.txt",
        configuration={"connector_document_acl": ["old"]},
    )
    doc_after = ConnectorDocument(
        id=doc_id,
        connector_id=doc_before.connector_id,
        file_path="/test/path.txt",
        file_name="path.txt",
        configuration={"connector_document_acl": ["new"]},
    )
    mock_doc_repo.get_by_id = AsyncMock(return_value=doc_before)
    mock_doc_repo.update = AsyncMock(return_value=doc_after)

    update = ConnectorDocumentUpdate(configuration={"connector_document_acl": ["new"]})

    with patch("asyncio.create_task") as mock_task:
        await document_service.update_document(doc_id, update)
        mock_task.assert_called()


@pytest.mark.asyncio
async def test_sync_document_nominal(document_service, mock_doc_repo, mock_ws_manager):
    """Test sync trigger."""
    doc = ConnectorDocument(id=uuid4(), connector_id=uuid4(), status=DocStatus.IDLE)
    mock_doc_repo.get_by_id = AsyncMock(return_value=doc)
    mock_doc_repo.update = AsyncMock()

    await document_service.sync_document(doc.id)
    assert (
        doc.status == DocStatus.IDLE
    )  # Status change should be reflected in update call not necessarily on object if not refreshed
    mock_doc_repo.update.assert_called_once()
    mock_ws_manager.emit_trigger_document_sync.assert_awaited()
