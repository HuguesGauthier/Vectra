from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.settings_service import get_settings_service

client = TestClient(app)


async def get_mock_settings_service_gemini():
    mock_service = AsyncMock()
    # Mock get_value to return key if it matches gemini, else None
    mock_service.get_value.side_effect = lambda key, default=None: "dummy-key" if key == "gemini_api_key" else None
    return mock_service


def test_get_providers_gemini_configured():
    # Override the dependency
    app.dependency_overrides[get_settings_service] = get_mock_settings_service_gemini

    response = client.get("/api/v1/providers/")
    assert response.status_code == 200
    data = response.json()

    # Check Gemini is configured
    gemini = next(p for p in data if p["id"] == "gemini" and p["type"] == "embedding")
    assert gemini["configured"] is True

    # Check OpenAI is NOT configured
    openai = next(p for p in data if p["id"] == "openai" and p["type"] == "embedding")
    assert openai["configured"] is False

    # Clean up
    app.dependency_overrides = {}


async def get_mock_settings_service_openai():
    mock_service = AsyncMock()
    mock_service.get_value.side_effect = lambda key, default=None: "sk-dummy" if key == "openai_api_key" else None
    return mock_service


def test_get_providers_openai_configured():
    app.dependency_overrides[get_settings_service] = get_mock_settings_service_openai

    response = client.get("/api/v1/providers/")
    assert response.status_code == 200
    data = response.json()

    gemini = next(p for p in data if p["id"] == "gemini" and p["type"] == "embedding")
    assert gemini["configured"] is False

    openai = next(p for p in data if p["id"] == "openai" and p["type"] == "embedding")
    assert openai["configured"] is True

    app.dependency_overrides = {}
