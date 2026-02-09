from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.v1.router import router
from app.core.database import get_db
from app.core.exceptions import EntityNotFound, VectraException
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.services.connector_service import (ConnectorService,
                                            get_connector_service)
from app.services.system_service import SystemService, get_system_service

# Setup App
app = FastAPI()
app.include_router(router, prefix="/api/v1")


# Exception Handlers
@app.exception_handler(VectraException)
async def vectra_exception_handler(request: Request, exc: VectraException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "code": exc.error_code},
    )


@app.exception_handler(EntityNotFound)
async def entity_not_found_handler(request: Request, exc: EntityNotFound):
    return JSONResponse(status_code=404, content={"message": str(exc)})


# Service Mocks
mock_connector_svc = AsyncMock(spec=ConnectorService)
mock_system_svc = AsyncMock(spec=SystemService)


# Dependency Overrides
async def override_get_connector_service():
    return mock_connector_svc


async def override_get_system_service():
    return mock_system_svc


async def override_get_db():
    mock_db = AsyncMock()
    yield mock_db


def override_get_admin():
    return User(
        id=uuid4(),
        email="admin@test.com",
        is_superuser=True,
        role="admin",
        is_active=True,
    )


def override_get_user():
    return User(
        id=uuid4(),
        email="user@test.com",
        is_superuser=False,
        role="user",
        is_active=True,
    )


app.dependency_overrides[get_connector_service] = override_get_connector_service
app.dependency_overrides[get_system_service] = override_get_system_service
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_admin] = override_get_admin
app.dependency_overrides[get_current_user] = override_get_user

client = TestClient(app)


class TestRoutes:

    def setup_method(self):
        mock_connector_svc.reset_mock()
        mock_system_svc.reset_mock()

    def test_get_connectors(self):
        """Test getting connectors list."""
        mock_connector_svc.get_connectors.return_value = []
        response = client.get("/api/v1/connectors/")

        assert response.status_code == 200
        assert response.json() == []

    def test_create_connector(self):
        """Test creating connector."""
        from app.models.connector import Connector

        mock_connector_svc.create_connector.return_value = Connector(
            id=uuid4(),
            name="test",
            connector_type="local_file",
            status="idle",
            configuration={},
            is_enabled=True,
        )

        response = client.post(
            "/api/v1/connectors/",
            json={"name": "test", "connector_type": "local_file", "configuration": {}},
        )
        assert response.status_code == 200
        mock_connector_svc.create_connector.assert_called_once()

    def test_open_file_security_check(self):
        """Test that open-file handle exceptions from service."""
        # System service raising EntityNotFound
        mock_system_svc.open_file_by_document_id.side_effect = EntityNotFound(
            "File not found"
        )

        doc_id = str(uuid4())
        response = client.post("/api/v1/system/open-file", json={"document_id": doc_id})

        # Should be 404 (EntityNotFound handler)
        assert response.status_code == 404
        assert "File not found" in response.json().get("message", "")

    def test_open_file_success(self):
        """Test successful file open logic."""
        mock_system_svc.open_file_by_document_id.return_value = True
        # Reset side effect
        mock_system_svc.open_file_by_document_id.side_effect = None

        doc_id = str(uuid4())
        response = client.post("/api/v1/system/open-file", json={"document_id": doc_id})

        assert response.status_code == 200
        mock_system_svc.open_file_by_document_id.assert_called_with(doc_id)
