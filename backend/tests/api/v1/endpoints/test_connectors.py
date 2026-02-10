import sys
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.connectors import router
from app.core.security import get_current_admin
from app.models.user import User
from app.services.connector_service import (ConnectorService,
                                            get_connector_service)
from app.services.document_service import DocumentService, get_document_service

app = FastAPI()
app.include_router(router, prefix="/api/v1/connectors")

# Mocks
mock_conn_svc = AsyncMock(spec=ConnectorService)
mock_doc_svc = AsyncMock(spec=DocumentService)


async def override_get_connector_service():
    return mock_conn_svc


async def override_get_document_service():
    return mock_doc_svc


def override_get_admin():
    return User(id=uuid4(), email="admin@test.com", is_superuser=True)


app.dependency_overrides[get_connector_service] = override_get_connector_service
app.dependency_overrides[get_document_service] = override_get_document_service
app.dependency_overrides[get_current_admin] = override_get_admin

client = TestClient(app)


class TestConnectors:

    def setup_method(self):
        mock_conn_svc.reset_mock()
        mock_doc_svc.reset_mock()

    def test_get_connectors(self):
        """Test listing connectors."""
        mock_conn_svc.get_connectors.return_value = []
        response = client.get("/api/v1/connectors/")
        assert response.status_code == 200
        mock_conn_svc.get_connectors.assert_called_once()

    def test_create_connector(self):
        """Test creating a connector."""
        connector_id = uuid4()
        data = {
            "name": "Test Connector",
            "connector_type": "local_file",
            "configuration": {},
            "schedule_type": "manual",
        }

        # Mock response needs to concrete values for Pydantic
        mock_response = MagicMock()
        mock_response.id = connector_id
        mock_response.name = data["name"]
        mock_response.description = None
        mock_response.connector_type = data["connector_type"]
        mock_response.configuration = data["configuration"]
        # Required fields by schema
        mock_response.schedule_type = data["schedule_type"]
        mock_response.schedule_cron = None
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"
        mock_response.last_vectorized_at = None
        mock_response.total_docs_count = 0
        mock_response.status = "idle"
        mock_response.credential_id = None
        mock_response.last_error = None

        mock_conn_svc.create_connector.return_value = mock_response

        response = client.post("/api/v1/connectors/", json=data)
        assert response.status_code == 200
        assert response.json()["id"] == str(connector_id)
        mock_conn_svc.create_connector.assert_called_once()

    def test_delete_connector(self):
        """Test deleting a connector."""
        conn_id = uuid4()
        response = client.delete(f"/api/v1/connectors/{conn_id}")
        assert response.status_code == 200
        mock_conn_svc.delete_connector.assert_called_once_with(conn_id)

    def test_get_connector_documents(self):
        """Test getting documents for a connector."""
        conn_id = uuid4()
        mock_doc_svc.get_connector_documents.return_value = {"items": [], "total": 0, "page": 1, "size": 20, "pages": 0}

        response = client.get(f"/api/v1/connectors/{conn_id}/documents")
        assert response.status_code == 200
        mock_doc_svc.get_connector_documents.assert_called_once()

    def test_trigger_sync(self):
        """Test manual sync trigger."""
        conn_id = uuid4()

        mock_response = MagicMock()
        mock_response.id = conn_id
        mock_response.name = "Test"
        mock_response.description = None
        mock_response.connector_type = "local_file"
        mock_response.configuration = {}
        mock_response.schedule_type = "manual"
        mock_response.schedule_cron = None
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"
        mock_response.last_vectorized_at = None
        mock_response.total_docs_count = 0
        mock_response.status = "queued"
        mock_response.credential_id = None
        mock_response.last_error = None

        mock_conn_svc.trigger_sync.return_value = mock_response

        response = client.post(f"/api/v1/connectors/{conn_id}/sync")
        assert response.status_code == 200
        mock_conn_svc.trigger_sync.assert_called_once()
