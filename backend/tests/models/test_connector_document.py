"""
Tests for ConnectorDocument model validation.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.enums import DocStatus
from app.schemas.documents import MAX_FILE_NAME_LENGTH, MAX_FILE_PATH_LENGTH, ConnectorDocumentBase


class TestConnectorDocumentValidation:
    """Test validation rules."""

    def test_valid_document_creation(self):
        """Valid document should pass validation."""
        doc = ConnectorDocumentBase(
            connector_id=uuid4(), file_path="/path/to/document.pdf", file_name="document.pdf", status=DocStatus.PENDING
        )
        assert doc.file_name == "document.pdf"
        assert doc.status == DocStatus.PENDING

    def test_file_path_too_long_fails(self):
        """File path exceeding max length should fail."""
        long_path = "a" * 3000  # Exceeds MAX_FILE_PATH_LENGTH (2048)

        with pytest.raises(ValidationError) as exc_info:
            ConnectorDocumentBase(connector_id=uuid4(), file_path=long_path, file_name="test.pdf")
        assert "file_path" in str(exc_info.value)

    def test_empty_file_name_fails(self):
        """Empty file name should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorDocumentBase(connector_id=uuid4(), file_path="/path/to/file", file_name="")
        assert "file_name" in str(exc_info.value)

    def test_negative_file_size_fails(self):
        """Negative file size should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorDocumentBase(connector_id=uuid4(), file_path="/path/to/file", file_name="test.pdf", file_size=-100)
        assert "file_size" in str(exc_info.value)

    def test_negative_metrics_fail(self):
        """Negative metrics should fail."""
        with pytest.raises(ValidationError) as exc_info:
            ConnectorDocumentBase(
                connector_id=uuid4(), file_path="/path/to/file", file_name="test.pdf", doc_token_count=-5
            )
        assert "doc_token_count" in str(exc_info.value)

    def test_valid_progress_tracking(self):
        """Valid progress tracking should work."""
        doc = ConnectorDocumentBase(
            connector_id=uuid4(), file_path="/path/to/file", file_name="test.pdf", chunks_total=100, chunks_processed=50
        )
        assert doc.chunks_total == 100
        assert doc.chunks_processed == 50

    def test_error_message_truncation(self):
        """Very long error messages should be constrained."""
        long_error = "x" * 3000  # Exceeds MAX_ERROR_MESSAGE_LENGTH (2000)

        with pytest.raises(ValidationError) as exc_info:
            ConnectorDocumentBase(
                connector_id=uuid4(), file_path="/path/to/file", file_name="test.pdf", error_message=long_error
            )
        assert "error_message" in str(exc_info.value)
