import pytest
from uuid import uuid4
from datetime import datetime, timezone
from app.schemas.documents import (
    ConnectorDocumentCreate,
    ConnectorDocumentUpdate,
    ConnectorDocumentResponse,
    ConnectorDocumentBase,
    DocStatus,
    MAX_FILE_PATH_LENGTH,
    MAX_FILE_NAME_LENGTH,
)


def test_document_create_basic():
    """Test basic ConnectorDocumentCreate."""
    doc = ConnectorDocumentCreate(file_path="/path/to/file.pdf", file_name="file.pdf", file_size=1024)
    assert doc.file_path == "/path/to/file.pdf"
    assert doc.file_name == "file.pdf"
    assert doc.file_size == 1024


def test_document_create_dos_protection_metadata():
    """Test DoS protection for configuration size (100KB limit)."""
    large_config = {"data": "x" * 101000}

    with pytest.raises(ValueError, match="Metadata/configuration too large"):
        ConnectorDocumentCreate(file_path="/path/to/file.pdf", file_name="file.pdf", configuration=large_config)


def test_document_create_valid_config():
    """Test valid configuration size."""
    valid_config = {"key": "value", "nested": {"data": "test"}}
    doc = ConnectorDocumentCreate(file_path="/path/to/file.pdf", file_name="file.pdf", configuration=valid_config)
    assert doc.configuration == valid_config


def test_document_create_path_length_validation():
    """Test file path length validation."""
    # Valid path
    doc = ConnectorDocumentCreate(file_path="/valid/path.pdf", file_name="file.pdf")
    assert doc.file_path == "/valid/path.pdf"

    # Too long path should fail
    with pytest.raises(ValueError):
        ConnectorDocumentCreate(file_path="x" * (MAX_FILE_PATH_LENGTH + 1), file_name="file.pdf")


def test_document_create_negative_file_size():
    """Test that negative file size is rejected."""
    with pytest.raises(ValueError):
        ConnectorDocumentCreate(file_path="/path/to/file.pdf", file_name="file.pdf", file_size=-100)


def test_document_update_partial():
    """Test partial updates with ConnectorDocumentUpdate."""
    update = ConnectorDocumentUpdate(file_name="updated.pdf", status=DocStatus.INDEXED)
    assert update.file_name == "updated.pdf"
    assert update.status == DocStatus.INDEXED
    assert update.file_path is None


def test_document_update_config_validation():
    """Test configuration validation in ConnectorDocumentUpdate."""
    # Valid config
    update = ConnectorDocumentUpdate(configuration={"key": "value"})
    assert update.configuration == {"key": "value"}

    # Too large config should fail
    with pytest.raises(ValueError, match="Metadata/configuration too large"):
        ConnectorDocumentUpdate(configuration={"data": "x" * 101000})


def test_document_base_defaults():
    """Test ConnectorDocumentBase default values."""
    doc = ConnectorDocumentBase(file_path="/path/to/file.pdf", file_name="file.pdf")
    assert doc.status == DocStatus.PENDING
    assert doc.file_metadata == {}
    assert doc.configuration == {}
    assert doc.chunks_total == 0
    assert doc.chunks_processed == 0


def test_document_base_metadata_dos_protection():
    """Test DoS protection for file_metadata."""
    large_metadata = {"data": "x" * 101000}

    with pytest.raises(ValueError, match="Metadata/configuration too large"):
        ConnectorDocumentBase(file_path="/path/to/file.pdf", file_name="file.pdf", file_metadata=large_metadata)


def test_document_response_structure():
    """Test ConnectorDocumentResponse has all required fields."""
    response = ConnectorDocumentResponse(
        id=uuid4(),
        connector_id=uuid4(),
        file_path="/path/to/file.pdf",
        file_name="file.pdf",
        status=DocStatus.INDEXED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert response.id is not None
    assert response.connector_id is not None
    assert response.status == DocStatus.INDEXED


def test_document_status_enum():
    """Test DocStatus enum validation."""
    doc = ConnectorDocumentBase(file_path="/path/to/file.pdf", file_name="file.pdf", status=DocStatus.PROCESSING)
    assert doc.status == DocStatus.PROCESSING


def test_document_processing_metrics():
    """Test processing metrics fields."""
    doc = ConnectorDocumentBase(
        file_path="/path/to/file.pdf",
        file_name="file.pdf",
        doc_token_count=1000,
        vector_point_count=50,
        processing_duration_ms=250.5,
        chunks_total=10,
        chunks_processed=8,
    )
    assert doc.doc_token_count == 1000
    assert doc.vector_point_count == 50
    assert doc.processing_duration_ms == 250.5
    assert doc.chunks_total == 10
    assert doc.chunks_processed == 8
