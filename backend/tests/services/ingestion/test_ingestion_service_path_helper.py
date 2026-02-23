from unittest.mock import Mock

import pytest

from app.services.ingestion_service import get_full_path_from_connector


class TestGetFullPathFromConnector:
    """Test the path reconstruction helper function."""

    def test_folder_connector_with_relative_path(self):
        """Test folder connector joins base_path with relative file_path."""
        connector = Mock(connector_type="local_folder", configuration={"path": "D:\\Documents"})
        result = get_full_path_from_connector(connector, "RH\\procedure.docx")
        assert result == "D:\\Documents\\RH\\procedure.docx"

    def test_file_connector_ignores_file_path(self):
        """Test file connector uses base_path directly (ignores file_path)."""
        connector = Mock(connector_type="local_file", configuration={"path": "D:\\Important\\budget.xlsx"})
        result = get_full_path_from_connector(connector, "budget.xlsx")
        # Should return base_path directly, NOT join with file_path
        assert result == "D:\\Important\\budget.xlsx"

    def test_file_connector_type_variations(self):
        """Test different variations of file connector type."""
        for conn_type in ["file", "local_file", "FILE", "Local_File"]:
            connector = Mock(connector_type=conn_type, configuration={"path": "D:\\test\\file.pdf"})
            result = get_full_path_from_connector(connector, "file.pdf")
            assert result == "D:\\test\\file.pdf"

    def test_folder_connector_type_variations(self):
        """Test different variations of folder connector type."""
        for conn_type in ["folder", "local_folder", "FOLDER", "Local_Folder"]:
            connector = Mock(connector_type=conn_type, configuration={"path": "D:\\base"})
            result = get_full_path_from_connector(connector, "sub\\file.txt")
            assert result == "D:\\base\\sub\\file.txt"

    def test_no_base_path_returns_file_path(self):
        """Test when configuration has no path, return file_path as-is."""
        connector = Mock(connector_type="local_folder", configuration={})
        result = get_full_path_from_connector(connector, "file.txt")
        assert result == "file.txt"

    def test_folder_connector_simple_filename(self):
        """Test folder connector with file at root (no subdirectory)."""
        connector = Mock(connector_type="local_folder", configuration={"path": "D:\\Documents"})
        result = get_full_path_from_connector(connector, "readme.txt")
        assert result == "D:\\Documents\\readme.txt"
