import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.pricing import get_pricing_service
from app.core.exceptions import TechnicalError
from app.schemas.pricing import PricingMapResponse


@pytest.fixture
def client():
    app.dependency_overrides = {}
    return TestClient(app)


def test_get_pricing_happy_path(client):
    """Verify successful pricing map retrieval."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_pricing_map.return_value = PricingMapResponse(
        prices={"gpt-4o": 0.0025, "gemini-1.5-flash": 0.00001875}, currency="USD"
    )
    app.dependency_overrides[get_pricing_service] = lambda: mock_service

    # Note: Router prefix is /pricing, so we call /api/v1/pricing/
    response = client.get("/api/v1/pricing/")

    assert response.status_code == 200
    data = response.json()
    assert data["prices"]["gpt-4o"] == 0.0025
    assert data["currency"] == "USD"
    mock_service.get_pricing_map.assert_called_once()


def test_get_pricing_technical_error(client):
    """Verify error handling when service raises an exception."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_pricing_map.side_effect = Exception("Service failure")
    app.dependency_overrides[get_pricing_service] = lambda: mock_service

    response = client.get("/api/v1/pricing/")

    assert response.status_code == 500
    assert response.json()["code"] == "PRICING_FETCH_ERROR"
