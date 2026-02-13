import sys
from unittest.mock import MagicMock

# Mock problematic dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal
from app.services.chat.source_service import SourceService


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_node():
    def _create_node(node_id="node_1", text="some text", metadata=None, score=0.9):
        node = MagicMock()
        node.node.node_id = node_id
        node.node.text = text
        node.node.metadata = metadata or {}
        node.node.get_content.return_value = text
        node.score = score
        return node

    return _create_node


@pytest.mark.asyncio
async def test_process_sources_happy_path(mock_db, mock_node):
    # Setup
    nodes = [
        mock_node(metadata={"file_path": "test.pdf", "file_name": "Test PDF"}),
        mock_node(metadata={"file_path": "data.docx"}),
    ]

    # Execute
    results = await SourceService.process_sources(nodes, mock_db)

    # Verify
    assert len(results) == 2
    assert results[0]["type"] == "pdf"
    assert results[0]["name"] == "Test PDF"
    assert results[1]["type"] == "docx"
    assert results[1]["name"] == "data.docx"
    assert results[0]["score"] == 0.9


@pytest.mark.asyncio
async def test_process_sources_db_fallback(mock_db, mock_node):
    # Setup
    doc_id = uuid4()
    nodes = [mock_node(metadata={"connector_document_id": str(doc_id)})]

    # Mock DB result
    mock_row = MagicMock()
    mock_row.id = doc_id
    mock_row.file_path = "db_file.pdf"
    mock_row.file_name = "DB File"

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    # Execute
    results = await SourceService.process_sources(nodes, mock_db)

    # Verify
    assert len(results) == 1
    assert results[0]["type"] == "pdf"
    assert results[0]["name"] == "DB File"
    assert results[0]["metadata"]["file_path"] == "db_file.pdf"  # Fallback worked


@pytest.mark.asyncio
async def test_process_sources_legacy_json_text(mock_db, mock_node):
    # Setup JSON text in node
    json_text = '{"text": "Extracted from JSON", "metadata": {"page_number": 5}}'
    nodes = [mock_node(text=json_text)]

    # Execute
    results = await SourceService.process_sources(nodes, mock_db)

    # Verify
    assert results[0]["text"] == "Extracted from JSON"
    assert results[0]["metadata"]["page_label"] == "5"


@pytest.mark.asyncio
async def test_process_sources_invalid_uuid(mock_db, mock_node):
    # Setup node with garbled connector_document_id
    nodes = [mock_node(metadata={"connector_document_id": "not-a-uuid"})]

    # Execute
    results = await SourceService.process_sources(nodes, mock_db)

    assert len(results) == 1
    # Verify DB was NOT called for invalid UUID
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_sanitize_data_types():
    data = {"dec": Decimal("10.5"), "nested": [{"val": Decimal("1.2")}], "uuid": uuid4()}

    sanitized = SourceService._sanitize_data(data)

    assert isinstance(sanitized["dec"], float)
    assert isinstance(sanitized["nested"][0]["val"], float)
    assert isinstance(sanitized["uuid"], str)
