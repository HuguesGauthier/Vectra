import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.router import router


@pytest.fixture
def client():
    return TestClient(app)


def test_router_prefixes_registered():
    """
    Verify that all expected prefixes are registered in the v1 router.
    """
    prefixes = [route.path for route in router.routes]

    expected_prefixes = [
        "/analytics",
        "/assistants",
        "/audio",
        "/auth",
        "/chat",
        "/connectors",
        "/dashboard",
        "/files",
        "/notifications",
        "/pricing",
        "/prompts",
        "/settings",
        "/system",
        "/trends",
        "/users",
    ]

    for prefix in expected_prefixes:
        assert any(p.startswith(prefix) for p in prefixes), f"Prefix {prefix} not found in router"


def test_router_app_integration(client):
    """
    Verify that the v1 router is correctly integrated into the main app.
    """
    # Check root health (from main.py)
    response = client.get("/health")
    assert response.status_code == 200

    # Check a v1 endpoint (auth/login)
    # We don't actually login, just check if the route is registered and returns 405 (method not allowed) or 422 (validation error) on GET
    response = client.get("/api/v1/auth/login")
    assert response.status_code == 405  # Should be POST only

    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
