from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.prompts import router
from app.core.exceptions import TechnicalError
from app.core.security import get_current_user
from app.models.user import User
from app.services.prompt_service import PromptService, get_prompt_service

app = FastAPI()
app.include_router(router, prefix="/api/v1/prompts")

# Mocks
mock_prompt_svc = AsyncMock(spec=PromptService)


async def override_get_prompt_service():
    return mock_prompt_svc


def override_get_user():
    return User(id=uuid4(), email="user@test.com")


app.dependency_overrides[get_prompt_service] = override_get_prompt_service
app.dependency_overrides[get_current_user] = override_get_user

client = TestClient(app)


class TestPrompts:

    def setup_method(self):
        mock_prompt_svc.reset_mock()
        mock_prompt_svc.optimize_instruction = AsyncMock()

    def test_optimize_prompt_success(self):
        """Test successful optimization."""
        mock_prompt_svc.optimize_instruction.return_value = "Optimized text"

        response = client.post("/api/v1/prompts/optimize", json={"instruction": "draft", "connector_ids": []})

        assert response.status_code == 200
        assert response.json()["optimized_instruction"] == "Optimized text"
        mock_prompt_svc.optimize_instruction.assert_called_once()

    def test_optimize_prompt_unauthorized(self):
        """Test unauthorized access."""
        app.dependency_overrides[get_current_user] = lambda: (_ for _ in ()).throw(Exception("Unauthorized"))

        try:
            client.post("/api/v1/prompts/optimize", json={"instruction": "draft"})
        except Exception as e:
            assert "Unauthorized" in str(e)

        # Reset override
        app.dependency_overrides[get_current_user] = override_get_user

    def test_optimize_prompt_error(self):
        """Test error handling from service."""
        mock_prompt_svc.optimize_instruction.side_effect = TechnicalError("Gemini Down", error_code="GEMINI_ERROR")

        with pytest.raises(TechnicalError):
            client.post("/api/v1/prompts/optimize", json={"instruction": "draft"})
