import pytest
import os
from unittest.mock import MagicMock
from app.core.interfaces.base_connector import get_full_path_from_connector


@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector.connector_type = "folder"
    connector.configuration = {"path": "C:\\Data\\Base" if os.name == "nt" else "/data/base"}
    return connector


def test_get_full_path_happy_path_folder(mock_connector):
    base = mock_connector.configuration["path"]
    rel = "subdir/file.txt"
    expected = os.path.abspath(os.path.join(base, rel))

    result = get_full_path_from_connector(mock_connector, rel)
    assert os.path.abspath(result) == expected


def test_get_full_path_happy_path_file(mock_connector):
    mock_connector.connector_type = "file"
    base = mock_connector.configuration["path"]

    result = get_full_path_from_connector(mock_connector, "any.txt")
    assert result == base


def test_get_full_path_empty_config():
    connector = MagicMock()
    connector.configuration = {}
    result = get_full_path_from_connector(connector, "fallback.txt")
    assert result == "fallback.txt"


def test_get_full_path_traversal_protection(mock_connector):
    base = mock_connector.configuration["path"]

    # Attempt to go up
    traversal_path = "../../etc/passwd" if os.name != "nt" else "..\\..\\Windows\\System32\\config"

    result = get_full_path_from_connector(mock_connector, traversal_path)

    # Should be constrained to base path
    assert result.startswith(os.path.abspath(base))
    # Should only contain the basename in the final part
    assert os.path.basename(result) in {"passwd", "config"}
    assert ".." not in result


def test_get_full_path_absolute_input_traversal(mock_connector):
    base = mock_connector.configuration["path"]

    # Absolute path input (should be treated as relative to base and not escape)
    abs_input = "/etc/passwd" if os.name != "nt" else "C:\\Windows\\System32\\config"

    result = get_full_path_from_connector(mock_connector, abs_input)

    assert result.startswith(os.path.abspath(base))
    assert "etc" not in result or result.count("etc") == 0  # Depending on how it joins
