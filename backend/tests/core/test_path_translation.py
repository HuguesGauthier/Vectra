import sys
from unittest.mock import MagicMock, patch
import pytest
from app.core.interfaces.base_connector import translate_host_path


@pytest.fixture
def mock_settings():
    with patch("app.core.settings.settings") as mock:
        yield mock


def test_translate_host_path_windows_native(mock_settings, monkeypatch):
    """Test translation on native Windows (no-op)."""
    monkeypatch.setattr(sys, "platform", "win32")
    path = "H:\\Formation\\Docs"
    # Should return original path
    assert translate_host_path(path) == path


def test_translate_host_path_docker_windows_host(mock_settings, monkeypatch):
    """Test translation in Docker (Linux) with a Windows host path."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_settings.VECTRA_DATA_PATH = "/data"
    mock_settings.VECTRA_DATA_PATH_HOST = "H:/"

    path = "H:\\Formation\\Docs"
    expected = "/data/Formation/Docs"

    assert translate_host_path(path) == expected


def test_translate_host_path_docker_windows_host_with_folder(mock_settings, monkeypatch):
    """Test translation in Docker (Linux) with a Windows host path that includes a folder."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_settings.VECTRA_DATA_PATH = "/data"
    mock_settings.VECTRA_DATA_PATH_HOST = "H:\\test"

    path = "H:\\test\\docs\\file.txt"
    expected = "/data/docs/file.txt"

    assert translate_host_path(path) == expected


def test_translate_host_path_docker_linux_host(mock_settings, monkeypatch):
    """Test translation in Docker (Linux) with a Linux host path."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_settings.VECTRA_DATA_PATH = "/data"
    mock_settings.VECTRA_DATA_PATH_HOST = "/home/user/vectra_data"

    path = "/home/user/vectra_data/projects/test"
    expected = "/data/projects/test"

    assert translate_host_path(path) == expected


def test_translate_host_path_no_match(mock_settings, monkeypatch):
    """Test behavior when path does not match prefix."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_settings.VECTRA_DATA_PATH = "/data"
    mock_settings.VECTRA_DATA_PATH_HOST = "H:/"

    path = "C:\\Other\\Path"
    # Should return original path if it doesn't match host prefix
    assert translate_host_path(path) == path
