from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.pricing import router
from app.core.exceptions import TechnicalError
from app.services.pricing_service import PricingService, get_pricing_service

app = FastAPI()
app.include_router(router, prefix="/api/v1")

# Mocks
mock_pricing_svc = MagicMock(spec=PricingService)


def override_get_pricing_service():
    return mock_pricing_svc


app.dependency_overrides[get_pricing_service] = override_get_pricing_service

client = TestClient(app)


class TestPricing:

    def setup_method(self):
        mock_pricing_svc.reset_mock()
        mock_pricing_svc.get_pricing_map = MagicMock()

    def test_get_pricing_success(self):
        """Test pricing retrieval."""
        mock_data = {"prices": {"gpt-4": 0.03, "local": 0.0}, "currency": "USD"}
        mock_pricing_svc.get_pricing_map = AsyncMock(return_value=mock_data)

        response = client.get("/api/v1/pricing")

        assert response.status_code == 200
        assert response.json()["prices"]["gpt-4"] == 0.03
        mock_pricing_svc.get_pricing_map.assert_called_once()

    def test_get_pricing_error(self):
        """Test error handling."""
        mock_pricing_svc.get_pricing_map.side_effect = Exception("Service Error")

        # Expect 500 (TechnicalError catches generic exception in controller and re-raises TechnicalError)
        with pytest.raises(TechnicalError):
            client.get("/api/v1/pricing")
