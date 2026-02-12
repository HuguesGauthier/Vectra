import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.prompts import get_prompt_service
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.enums import UserRole
from app.core.exceptions import FunctionalError, TechnicalError

# Mock Data
USER_ID = uuid4()
mock_user = User(id=USER_ID, email="user@example.com", role=UserRole.USER, is_active=True)


# Dependency Overrides
async def override_get_current_user():
    return mock_user


@pytest.fixture
def client():
    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def test_optimize_prompt_happy_path(client):
    """Verify successful prompt optimization."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.optimize_instruction.return_value = "Optimized instruction"
    app.dependency_overrides[get_prompt_service] = lambda: mock_service

    response = client.post(
        "/api/v1/prompts/optimize", json={"instruction": "Original instruction", "connector_ids": []}
    )

    assert response.status_code == 200
    assert response.json() == {"optimized_instruction": "Optimized instruction"}
    mock_service.optimize_instruction.assert_called_once_with("Original instruction")


def test_optimize_prompt_validation_error_empty(client):
    """Verify that empty instruction is rejected."""
    response = client.post("/api/v1/prompts/optimize", json={"instruction": "", "connector_ids": []})
    assert response.status_code == 422


def test_optimize_prompt_validation_error_too_long(client):
    """Verify that too long instruction is rejected."""
    long_instruction = "a" * 5001
    response = client.post("/api/v1/prompts/optimize", json={"instruction": long_instruction, "connector_ids": []})
    assert response.status_code == 422


def test_optimize_prompt_functional_error(client):
    """Verify functional error handling."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.optimize_instruction.side_effect = FunctionalError(
        message="Functional optimization failure", error_code="FUNC_ERR"
    )
    app.dependency_overrides[get_prompt_service] = lambda: mock_service

    response = client.post("/api/v1/prompts/optimize", json={"instruction": "test", "connector_ids": []})

    assert response.status_code == 400
    assert response.json()["code"] == "FUNC_ERR"


def test_optimize_prompt_technical_error(client):
    """Verify technical error handling."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.optimize_instruction.side_effect = TechnicalError(
        message="Technical optimization failure", error_code="TECH_ERR"
    )
    app.dependency_overrides[get_prompt_service] = lambda: mock_service

    response = client.post("/api/v1/prompts/optimize", json={"instruction": "test", "connector_ids": []})

    assert response.status_code == 500
    assert response.json()["code"] == "TECH_ERR"


def test_optimize_prompt_unexpected_error(client):
    """Verify fallback to TechnicalError for unexpected exceptions."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.optimize_instruction.side_effect = Exception("Boom")
    app.dependency_overrides[get_prompt_service] = lambda: mock_service

    response = client.post("/api/v1/prompts/optimize", json={"instruction": "test", "connector_ids": []})

    assert response.status_code == 500
    assert response.json()["code"] == "PROMPT_OPTIMIZATION_FAILED"
