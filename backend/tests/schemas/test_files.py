"""
Unit tests for backend/app/schemas/files.py

Tests cover:
- Happy path: Valid file streaming info creation
- Edge cases: Empty strings, special characters, long paths
- Validation: Missing required fields
"""

import pytest
from pydantic import ValidationError

from app.schemas.files import FileStreamingInfo


class TestFileStreamingInfo:
    """Test suite for FileStreamingInfo schema."""

    # ========== HAPPY PATH ==========

    def test_create_valid_file_streaming_info(self):
        """Test creating a valid FileStreamingInfo instance."""
        data = {
            "file_path": "/absolute/path/to/document.pdf",
            "media_type": "application/pdf",
            "file_name": "document.pdf",
        }

        file_info = FileStreamingInfo(**data)

        assert file_info.file_path == "/absolute/path/to/document.pdf"
        assert file_info.media_type == "application/pdf"
        assert file_info.file_name == "document.pdf"

    def test_create_with_windows_path(self):
        """Test creating FileStreamingInfo with Windows-style path."""
        data = {
            "file_path": "C:\\Users\\Documents\\report.xlsx",
            "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "file_name": "report.xlsx",
        }

        file_info = FileStreamingInfo(**data)

        assert file_info.file_path == "C:\\Users\\Documents\\report.xlsx"
        assert file_info.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert file_info.file_name == "report.xlsx"

    def test_create_with_special_characters_in_filename(self):
        """Test creating FileStreamingInfo with special characters in filename."""
        data = {
            "file_path": "/tmp/file with spaces & special-chars_123.txt",
            "media_type": "text/plain",
            "file_name": "file with spaces & special-chars_123.txt",
        }

        file_info = FileStreamingInfo(**data)

        assert file_info.file_name == "file with spaces & special-chars_123.txt"

    def test_model_dump(self):
        """Test serialization of FileStreamingInfo to dict."""
        data = {
            "file_path": "/path/to/file.json",
            "media_type": "application/json",
            "file_name": "file.json",
        }

        file_info = FileStreamingInfo(**data)
        dumped = file_info.model_dump()

        assert dumped == data

    def test_model_dump_json(self):
        """Test JSON serialization of FileStreamingInfo."""
        data = {
            "file_path": "/path/to/image.png",
            "media_type": "image/png",
            "file_name": "image.png",
        }

        file_info = FileStreamingInfo(**data)
        json_str = file_info.model_dump_json()

        assert '"file_path":"/path/to/image.png"' in json_str
        assert '"media_type":"image/png"' in json_str
        assert '"file_name":"image.png"' in json_str

    # ========== EDGE CASES ==========

    def test_create_with_very_long_path(self):
        """Test creating FileStreamingInfo with extremely long file path."""
        long_path = "/very/" + "long/" * 100 + "path/to/file.txt"
        data = {
            "file_path": long_path,
            "media_type": "text/plain",
            "file_name": "file.txt",
        }

        file_info = FileStreamingInfo(**data)

        assert file_info.file_path == long_path

    def test_create_with_unicode_filename(self):
        """Test creating FileStreamingInfo with Unicode characters in filename."""
        data = {
            "file_path": "/tmp/文档.pdf",
            "media_type": "application/pdf",
            "file_name": "文档.pdf",
        }

        file_info = FileStreamingInfo(**data)

        assert file_info.file_name == "文档.pdf"

    def test_create_with_empty_strings(self):
        """Test creating FileStreamingInfo with empty strings (should succeed - Pydantic allows it)."""
        data = {
            "file_path": "",
            "media_type": "",
            "file_name": "",
        }

        # Pydantic allows empty strings by default for str fields
        file_info = FileStreamingInfo(**data)

        assert file_info.file_path == ""
        assert file_info.media_type == ""
        assert file_info.file_name == ""

    # ========== VALIDATION ERRORS (WORST CASE) ==========

    def test_missing_file_path_raises_validation_error(self):
        """Test that missing file_path raises ValidationError."""
        data = {
            "media_type": "application/pdf",
            "file_name": "document.pdf",
        }

        with pytest.raises(ValidationError) as exc_info:
            FileStreamingInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("file_path",)
        assert errors[0]["type"] == "missing"

    def test_missing_media_type_raises_validation_error(self):
        """Test that missing media_type raises ValidationError."""
        data = {
            "file_path": "/path/to/file.pdf",
            "file_name": "document.pdf",
        }

        with pytest.raises(ValidationError) as exc_info:
            FileStreamingInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("media_type",)
        assert errors[0]["type"] == "missing"

    def test_missing_file_name_raises_validation_error(self):
        """Test that missing file_name raises ValidationError."""
        data = {
            "file_path": "/path/to/file.pdf",
            "media_type": "application/pdf",
        }

        with pytest.raises(ValidationError) as exc_info:
            FileStreamingInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("file_name",)
        assert errors[0]["type"] == "missing"

    def test_missing_all_fields_raises_validation_error(self):
        """Test that missing all required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FileStreamingInfo()

        errors = exc_info.value.errors()
        assert len(errors) == 3
        field_names = {error["loc"][0] for error in errors}
        assert field_names == {"file_path", "media_type", "file_name"}

    def test_invalid_field_type_raises_validation_error(self):
        """Test that invalid field types raise ValidationError."""
        data = {
            "file_path": 123,  # Should be str
            "media_type": "application/pdf",
            "file_name": "document.pdf",
        }

        with pytest.raises(ValidationError) as exc_info:
            FileStreamingInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("file_path",)
        assert errors[0]["type"] == "string_type"

    def test_none_values_raise_validation_error(self):
        """Test that None values for required fields raise ValidationError."""
        data = {
            "file_path": None,
            "media_type": None,
            "file_name": None,
        }

        with pytest.raises(ValidationError) as exc_info:
            FileStreamingInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 3
        for error in errors:
            assert error["type"] == "string_type"
