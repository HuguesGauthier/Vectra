import pytest
import os
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.document_repository import DocumentRepository
from app.models.connector_document import ConnectorDocument
from app.schemas.enums import DocStatus
from app.core.exceptions import TechnicalError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.document_repository.select") as mock:
        yield mock


@pytest.fixture
def document_repo(mock_db):
    return DocumentRepository(db=mock_db)


@pytest.mark.asyncio
async def test_upsert_logic(document_repo, mock_db):
    """Test batch upsert logic (atomic transaction)."""
    connector_id = uuid4()

    # Mock docs
    doc1 = MagicMock()
    doc1.id_ = "path/doc1.txt"
    doc1.metadata = {"file_path": "path/doc1.txt"}

    doc2 = MagicMock()
    doc2.id_ = "path/doc2.txt"
    doc2.metadata = {"file_path": "path/doc2.txt"}

    llama_docs = [doc1, doc2]

    # Mock get_by_file_path behavior using side_effect
    # First call: None (create new)
    # Second call: MagicMock (update existing)
    existing_doc = MagicMock(spec=ConnectorDocument)
    existing_doc.id = uuid4()

    # We need to simulate get_by_file_path calls
    with patch.object(document_repo, "get_by_file_path", side_effect=[None, existing_doc]):
        result = await document_repo.upsert_connector_documents(connector_id, llama_docs)

        assert len(result) == 2
        # Verify 1 add (doc1)
        # Verify 1 update (doc2) -> existing_doc updated

        # Verify single commit
        mock_db.commit.assert_called_once()

        # Verify updates on existing doc
        assert existing_doc.status == DocStatus.INDEXED


@pytest.mark.asyncio
async def test_upsert_rollback_on_error(document_repo, mock_db):
    """Test entire batch rolls back if one fails."""
    connector_id = uuid4()
    doc1 = MagicMock()
    doc1.id_ = "path/doc1.txt"
    doc1.metadata = {}

    # Mock error on commit
    mock_db.commit.side_effect = SQLAlchemyError("DB Error")

    with patch.object(document_repo, "get_by_file_path", return_value=None):
        with pytest.raises(TechnicalError):
            await document_repo.upsert_connector_documents(connector_id, [doc1])

        mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_search_documents(document_repo, mock_db):
    """Test search query construction."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    await document_repo.search_documents(connector_id=uuid4(), search_term="test", status=DocStatus.INDEXED)

    mock_db.execute.assert_called_once()
    # Analyzing the call args is complex with SQLAlchemy expressions,
    # ensuring it runs without error is a good first step.


@pytest.mark.asyncio
async def test_get_aggregate_stats(document_repo, mock_db):
    """Test stats aggregation."""
    mock_row = MagicMock()
    mock_row.total_docs = 10
    mock_row.total_tokens = 1000
    mock_row.total_vectors = 50

    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    mock_db.execute.return_value = mock_result

    stats = await document_repo.get_aggregate_stats()

    assert stats["total_docs"] == 10
    assert stats["total_tokens"] == 1000
    assert stats["total_vectors"] == 50
