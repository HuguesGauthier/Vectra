"""
Tests for Document Schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.documents import (ConnectorDocumentBase,
                                   ConnectorDocumentCreate,
                                   ConnectorDocumentUpdate)


def test_document_validation_size():
    big_dict = {"data": "a" * 100001}
    with pytest.raises(ValidationError) as exc:
        ConnectorDocumentCreate(file_path="/tmp/test", file_name="test.txt", configuration=big_dict)
    assert "too large" in str(exc.value)


def test_document_validation_chunks():
    # Success
    b = ConnectorDocumentBase(file_path="p", file_name="n", chunks_total=10, chunks_processed=5)
    assert b.chunks_processed == 5

    # Failure
    with pytest.raises(ValidationError) as exc:
        ConnectorDocumentBase(file_path="p", file_name="n", chunks_total=5, chunks_processed=10)
    assert "cannot > chunks_total" in str(exc.value)


def test_document_update_fields():
    u = ConnectorDocumentUpdate(file_name="new.txt")
    assert u.file_path is None
    assert u.file_name == "new.txt"
