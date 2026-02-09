from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.v1.endpoints.auth import router
from app.core.exceptions import FunctionalError, TechnicalError
from app.schemas.token import Token
from app.services.auth_service import AuthService, get_auth_service

app = FastAPI()
app.include_router(router, prefix="/api/v1/auth")

# Mocks
mock_auth_svc = AsyncMock(spec=AuthService)


async def override_get_auth_service():
    return mock_auth_svc


app.dependency_overrides[get_auth_service] = override_get_auth_service

client = TestClient(app)


class TestAuth:

    def setup_method(self):
        mock_auth_svc.reset_mock()
        mock_auth_svc.authenticate = AsyncMock()

    def test_login_success(self):
        """Test successful login returns token."""
        # Arrange
        expected_token = Token(access_token="fake-jwt", token_type="bearer")
        mock_auth_svc.authenticate.return_value = expected_token

        form_data = {"username": "user@example.com", "password": "password123"}

        # Act
        response = client.post("/api/v1/auth/login", data=form_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "fake-jwt"
        assert data["token_type"] == "bearer"

        # Verify dependency call
        mock_auth_svc.authenticate.assert_called_once_with("user@example.com", "password123")

    def test_login_failure_invalid_creds(self):
        """Test login failure with standard FunctionalError."""
        # Arrange
        mock_auth_svc.authenticate.side_effect = FunctionalError(
            message="Incorrect email or password", error_code="INVALID_CREDENTIALS", status_code=400
        )

        form_data = {"username": "user@example.com", "password": "wrongpassword"}

        # Act
        with pytest.raises(FunctionalError) as excinfo:
            client.post("/api/v1/auth/login", data=form_data)

        assert excinfo.value.status_code == 400
        assert excinfo.value.error_code == "INVALID_CREDENTIALS"

    def test_login_failure_technical_error(self):
        """Test login failure with TechnicalError."""
        # Arrange
        mock_auth_svc.authenticate.side_effect = TechnicalError(
            message="Database connection failed", error_code="DB_ERROR"
        )

        form_data = {"username": "user@example.com", "password": "password123"}

        # Act
        with pytest.raises(TechnicalError) as excinfo:
            client.post("/api/v1/auth/login", data=form_data)

        assert excinfo.value.message == "Database connection failed"
        assert excinfo.value.error_code == "DB_ERROR"

    def test_login_failure_unexpected_exception(self):
        """Test login failure with unexpected exception."""
        # Arrange
        mock_auth_svc.authenticate.side_effect = ValueError("Something went wrong")

        form_data = {"username": "user@example.com", "password": "password123"}

        # Act
        with pytest.raises(TechnicalError) as excinfo:
            client.post("/api/v1/auth/login", data=form_data)

        assert excinfo.value.message == "Login failed"
