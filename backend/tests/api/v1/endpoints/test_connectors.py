import sys
from typing import List
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.connectors import router
from app.core.security import get_current_admin
from app.models.user import User
from app.services.connector_service import ConnectorService, get_connector_service
from app.services.document_service import DocumentService, get_document_service
from app.services.sql_discovery_service import get_sql_discovery_service

app = FastAPI()
app.include_router(router, prefix="/api/v1/connectors")

# Mocks
mock_conn_svc = AsyncMock(spec=ConnectorService)
mock_doc_svc = AsyncMock(spec=DocumentService)
# Link to doc repo mock
mock_doc_svc.document_repo = MagicMock()
mock_doc_svc.document_repo.get_by_id = AsyncMock()
mock_sql_svc = AsyncMock()


async def override_get_connector_service():
    return mock_conn_svc


async def override_get_document_service():
    return mock_doc_svc


async def override_get_sql_discovery_service():
    return mock_sql_svc


def override_get_admin():
    return User(id=uuid4(), email="admin@test.com", is_superuser=True)


app.dependency_overrides[get_connector_service] = override_get_connector_service
app.dependency_overrides[get_document_service] = override_get_document_service
app.dependency_overrides[get_current_admin] = override_get_admin
app.dependency_overrides[get_sql_discovery_service] = override_get_sql_discovery_service

client = TestClient(app)


class TestConnectors:

    def setup_method(self):
        mock_conn_svc.reset_mock()
        mock_doc_svc.reset_mock()
        mock_doc_svc.document_repo.get_by_id.reset_mock()
        mock_sql_svc.reset_mock()

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

    def test_test_connection_sql_success(self):
        payload = {"connector_type": "sql", "configuration": {"host": "localhost"}}
        mock_sql_svc.test_connection.return_value = True
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 200
        assert response.json() == {"success": True, "message": "Connection successful"}
        mock_sql_svc.test_connection.assert_called_once_with(payload["configuration"])

    def test_test_connection_sql_failure(self):
        payload = {"connector_type": "sql", "configuration": {"host": "localhost"}}
        mock_sql_svc.test_connection.side_effect = Exception("Conn error")
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 200
        assert response.json() == {"success": False, "message": "Conn error"}

    def test_test_connection_missing_params(self):
        payload = {"connector_type": "sql"}
        # Schema validation will return 422, not 200 with success: False
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 422

    def test_test_connection_not_implemented(self):
        payload = {"connector_type": "unsupported", "configuration": {"foo": "bar"}}
        # Schema validation will return 422 for invalid enum value
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 422

    def test_update_connector(self):
        conn_id = uuid4()
        data = {"name": "Updated Name"}
        mock_response = MagicMock()
        mock_response.id = conn_id
        mock_response.name = "Updated Name"
        # Mocking all required fields for ConnectorResponse
        fields = [
            "description",
            "connector_type",
            "configuration",
            "schedule_type",
            "schedule_cron",
            "created_at",
            "updated_at",
            "last_vectorized_at",
            "total_docs_count",
            "status",
            "credential_id",
            "last_error",
        ]
        for field in fields:
            setattr(mock_response, field, None)
        mock_response.connector_type = "local_file"
        mock_response.configuration = {}
        mock_response.schedule_type = "manual"
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"
        mock_response.total_docs_count = 0
        mock_response.status = "idle"

        mock_conn_svc.update_connector.return_value = mock_response
        response = client.put(f"/api/v1/connectors/{conn_id}", json=data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_scan_connector_files(self):
        conn_id = uuid4()
        mock_response = MagicMock()
        mock_response.id = conn_id
        fields = [
            "name",
            "description",
            "connector_type",
            "configuration",
            "schedule_type",
            "schedule_cron",
            "created_at",
            "updated_at",
            "last_vectorized_at",
            "total_docs_count",
            "status",
            "credential_id",
            "last_error",
        ]
        for field in fields:
            setattr(mock_response, field, None)
        mock_response.name = "Test"
        mock_response.connector_type = "local_folder"
        mock_response.configuration = {}
        mock_response.schedule_type = "manual"
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"
        mock_response.total_docs_count = 0
        mock_response.status = "syncing"

        mock_conn_svc.scan_connector.return_value = mock_response
        response = client.post(f"/api/v1/connectors/{conn_id}/scan-files")
        assert response.status_code == 200
        mock_conn_svc.scan_connector.assert_called_once_with(conn_id)

    def test_stop_connector(self):
        conn_id = uuid4()
        mock_response = MagicMock()
        mock_response.id = conn_id
        # Set required fields
        for field in [
            "name",
            "description",
            "connector_type",
            "configuration",
            "schedule_type",
            "schedule_cron",
            "created_at",
            "updated_at",
            "last_vectorized_at",
            "total_docs_count",
            "status",
            "credential_id",
            "last_error",
        ]:
            setattr(mock_response, field, None)
        mock_response.name = "Test"
        mock_response.connector_type = "local_folder"
        mock_response.configuration = {}
        mock_response.schedule_type = "manual"
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"
        mock_response.total_docs_count = 0
        mock_response.status = "idle"

        mock_conn_svc.stop_connector.return_value = mock_response
        response = client.post(f"/api/v1/connectors/{conn_id}/stop")
        assert response.status_code == 200
        mock_conn_svc.stop_connector.assert_called_once_with(conn_id)

    def test_train_vanna_connector_success(self):
        conn_id = uuid4()
        doc_id = uuid4()
        payload = {"document_ids": [str(doc_id)]}

        mock_conn_svc.train_vanna.return_value = {
            "success": True,
            "message": "Training completed. 1 documents trained, 0 failed.",
            "trained_count": 1,
            "failed_count": 0,
        }

        response = client.post(f"/api/v1/connectors/{conn_id}/train", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["trained_count"] == 1
        mock_conn_svc.train_vanna.assert_called_once()

    def test_train_vanna_not_found(self):
        conn_id = uuid4()
        mock_conn_svc.train_vanna.return_value = {"success": False, "message": "Connector not found"}
        response = client.post(f"/api/v1/connectors/{conn_id}/train", json={"document_ids": [str(uuid4())]})
        assert response.json()["message"] == "Connector not found"

    def test_train_vanna_wrong_type(self):
        conn_id = uuid4()
        mock_conn_svc.train_vanna.return_value = {
            "success": False,
            "message": "Training is only available for vanna_sql connectors",
        }
        response = client.post(f"/api/v1/connectors/{conn_id}/train", json={"document_ids": [str(uuid4())]})
        assert "only available for vanna_sql" in response.json()["message"]

    def test_create_connector_document(self):
        conn_id = uuid4()
        data = {"file_path": "test.txt", "file_name": "test.txt"}
        mock_response = MagicMock()
        mock_response.id = uuid4()
        mock_response.connector_id = conn_id
        mock_response.file_path = "test.txt"
        mock_response.file_name = "test.txt"
        mock_response.status = "pending"
        # Add other required fields from ConnectorDocumentResponse/Base
        mock_response.last_modified_at_source = None
        mock_response.last_vectorized_at = None
        mock_response.file_size = None
        mock_response.error_message = None
        mock_response.file_metadata = {}
        mock_response.configuration = {}
        mock_response.mime_type = None
        mock_response.doc_token_count = 0
        mock_response.vector_point_count = 0
        mock_response.processing_duration_ms = 0.0
        mock_response.chunks_total = 0
        mock_response.chunks_processed = 0
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"

        mock_doc_svc.create_document.return_value = mock_response
        response = client.post(f"/api/v1/connectors/{conn_id}/documents", json=data)
        assert response.status_code == 200
        assert response.json()["file_name"] == "test.txt"

    def test_delete_document(self):
        conn_id = uuid4()
        doc_id = uuid4()
        response = client.delete(f"/api/v1/connectors/{conn_id}/documents/{doc_id}")
        assert response.status_code == 200
        mock_doc_svc.delete_document.assert_called_once_with(doc_id)

    def test_update_document(self):
        conn_id = uuid4()
        doc_id = uuid4()
        data = {"file_name": "new_name.txt"}
        mock_response = MagicMock()
        mock_response.id = doc_id
        mock_response.connector_id = conn_id
        mock_response.file_path = "test.txt"
        mock_response.file_name = "new_name.txt"
        mock_response.status = "pending"
        mock_response.last_modified_at_source = None
        mock_response.last_vectorized_at = None
        mock_response.file_size = None
        mock_response.error_message = None
        mock_response.file_metadata = {}
        mock_response.configuration = {}
        mock_response.mime_type = None
        mock_response.doc_token_count = 0
        mock_response.vector_point_count = 0
        mock_response.processing_duration_ms = 0.0
        mock_response.chunks_total = 0
        mock_response.chunks_processed = 0
        mock_response.created_at = "2024-01-01T00:00:00"
        mock_response.updated_at = "2024-01-01T00:00:00"

        mock_doc_svc.update_document.return_value = mock_response
        response = client.put(f"/api/v1/connectors/{conn_id}/documents/{doc_id}", json=data)
        assert response.status_code == 200
        assert response.json()["file_name"] == "new_name.txt"

    def test_stop_document(self):
        conn_id = uuid4()
        doc_id = uuid4()
        response = client.post(f"/api/v1/connectors/{conn_id}/documents/{doc_id}/stop")
        assert response.status_code == 200
        mock_doc_svc.stop_document.assert_called_once_with(doc_id)

    def test_sync_document(self):
        conn_id = uuid4()
        doc_id = uuid4()
        response = client.post(f"/api/v1/connectors/{conn_id}/documents/{doc_id}/sync")
        assert response.status_code == 200
        mock_doc_svc.sync_document.assert_called_once_with(doc_id)
