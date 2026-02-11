import sys
from unittest.mock import MagicMock, patch
import pytest
import os
from llama_index.core import Document

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.services.ingestion.connectors.folder_connector import FolderConnector
from app.schemas.ingestion import FolderIngestionConfig


@pytest.fixture
def connector():
    return FolderConnector()


@pytest.mark.asyncio
async def test_validate_config_dir_exists(connector):
    """Happy Path: validates an existing directory."""
    config = FolderIngestionConfig(path="existing_dir")
    with patch("os.path.isdir", return_value=True):
        assert await connector.validate_config(config) is True


@pytest.mark.asyncio
async def test_validate_config_not_a_dir(connector):
    """Worst Case: rejects a path that is not a directory."""
    config = FolderIngestionConfig(path="existing_file.txt")
    with patch("os.path.isdir", return_value=False):
        assert await connector.validate_config(config) is False


@pytest.mark.asyncio
async def test_load_data_success(connector, tmp_path):
    """Happy Path: loads documents from a folder and enforces relative paths."""
    # Create a real temporary structure
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    sub_dir = docs_dir / "sub"
    sub_dir.mkdir()
    test_file = sub_dir / "file.txt"
    test_file.write_text("test content")

    config = FolderIngestionConfig(path=str(docs_dir), recursive=True)

    # We still mock SimpleDirectoryReader because we don't want to actually
    # run LlamaIndex's complex loading, but we use real paths.
    mock_doc = Document(text="test content", metadata={"file_path": str(test_file)})
    mock_doc.id_ = str(test_file)

    with (
        patch("os.path.isdir", return_value=True),
        patch("app.services.ingestion.connectors.folder_connector.SimpleDirectoryReader") as mock_reader_cls,
    ):
        mock_reader = mock_reader_cls.return_value
        mock_reader.load_data.return_value = [mock_doc]

        docs = await connector.load_data(config)

        assert len(docs) == 1
        # Use os.path.join/relpath to check cross-platform result
        expected_rel = os.path.join("sub", "file.txt")
        assert docs[0].metadata["file_path"] == expected_rel
        assert docs[0].id_ == expected_rel


@pytest.mark.asyncio
async def test_load_data_with_patterns(connector, tmp_path):
    """Test that patterns are passed to SimpleDirectoryReader."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config = FolderIngestionConfig(path=str(docs_dir), patterns=[".pdf", "docx"])

    with (
        patch("os.path.isdir", return_value=True),
        patch("app.services.ingestion.connectors.folder_connector.SimpleDirectoryReader") as mock_reader_cls,
    ):
        mock_reader = mock_reader_cls.return_value
        mock_reader.load_data.return_value = []

        await connector.load_data(config)

        # Check if SimpleDirectoryReader was initialized with correct required_exts
        args, kwargs = mock_reader_cls.call_args
        assert kwargs["required_exts"] == [".pdf", ".docx"]


@pytest.mark.asyncio
async def test_load_data_invalid_config(connector):
    """Worst Case: error when folder is invalid."""
    config = FolderIngestionConfig(path="missing_dir")
    with patch("os.path.isdir", return_value=False):
        with pytest.raises(ValueError, match="Invalid configuration or folder not found"):
            await connector.load_data(config)


@pytest.mark.asyncio
async def test_load_data_runtime_error(connector):
    """Test mapping of internal exceptions to RuntimeError."""
    config = FolderIngestionConfig(path="/data/docs")
    with (
        patch("os.path.isdir", return_value=True),
        patch(
            "app.services.ingestion.connectors.folder_connector.SimpleDirectoryReader",
            side_effect=Exception("Disk failure"),
        ),
    ):
        with pytest.raises(RuntimeError, match="Failed to ingest folder"):
            await connector.load_data(config)
