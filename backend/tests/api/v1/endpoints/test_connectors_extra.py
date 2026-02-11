import sys
from unittest.mock import MagicMock

# Mock vanna before it's imported
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch
from app.api.v1.endpoints.connectors import router
from app.services.connector_service import get_connector_service, ConnectorService
from app.services.document_service import get_document_service, DocumentService
from app.services.sql_discovery_service import get_sql_discovery_service
from app.core.security import get_current_admin
from app.models.user import User
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/v1/connectors")

mock_conn_svc = AsyncMock(spec=ConnectorService)
mock_doc_svc = AsyncMock(spec=DocumentService)
# Add document_repo to mock_doc_svc
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
app.dependency_overrides[get_sql_discovery_service] = override_get_sql_discovery_service
app.dependency_overrides[get_current_admin] = override_get_admin

client = TestClient(app)


class TestConnectorsExtra:
    def setup_method(self):
        mock_conn_svc.reset_mock()
        mock_doc_svc.reset_mock()
        mock_doc_svc.document_repo.get_by_id.reset_mock()
        mock_sql_svc.reset_mock()

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
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is False

    def test_test_connection_not_implemented(self):
        payload = {"connector_type": "unsupported", "configuration": {"foo": "bar"}}
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 200
        assert "not implemented" in response.json()["message"]

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

    @patch("app.services.chat.vanna_services.VannaServiceFactory", new_callable=AsyncMock)
    def test_train_vanna_connector_success(self, mock_vanna_factory):
        conn_id = uuid4()
        doc_id = uuid4()
        payload = {"document_ids": [str(doc_id)]}

        mock_connector = MagicMock()
        mock_connector.connector_type = "vanna_sql"
        mock_conn_svc.get_connector.return_value = mock_connector

        mock_vanna_svc = MagicMock()
        mock_vanna_factory.return_value = mock_vanna_svc

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.file_name = "test_view"
        mock_doc.file_metadata = {"ddl": "CREATE VIEW ..."}
        mock_doc_svc.document_repo.get_by_id.return_value = mock_doc

        response = client.post(f"/api/v1/connectors/{conn_id}/train", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["trained_count"] == 1

    def test_train_vanna_not_found(self):
        conn_id = uuid4()
        mock_conn_svc.get_connector.return_value = None
        response = client.post(f"/api/v1/connectors/{conn_id}/train", json={"document_ids": ["some-id"]})
        assert response.json()["message"] == "Connector not found"

    def test_train_vanna_wrong_type(self):
        conn_id = uuid4()
        mock_connector = MagicMock()
        mock_connector.connector_type = "local_file"
        mock_conn_svc.get_connector.return_value = mock_connector
        response = client.post(f"/api/v1/connectors/{conn_id}/train", json={"document_ids": ["some-id"]})
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
