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
from tests.utils import get_test_app

app = get_test_app()
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
    return User(id=uuid4(), email="admin@test.com", is_superuser=True, hashed_password="placeholder")


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
        # Missing configuration triggers 422 Validation Error
        assert response.status_code == 422

    def test_test_connection_not_implemented(self):
        from app.schemas.enums import ConnectorType

        payload = {"connector_type": ConnectorType.LOCAL_FILE, "configuration": {"foo": "bar"}}
        response = client.post("/api/v1/connectors/test-connection", json=payload)
        assert response.status_code == 200
        assert "not implemented" in response.json()["message"]

    def test_update_connector(self):
        from app.schemas.connector import ConnectorResponse
        from app.schemas.enums import ConnectorStatus, ConnectorType, ScheduleType

        conn_id = uuid4()
        data = {"name": "Updated Name"}

        mock_response = ConnectorResponse(
            id=conn_id,
            name="Updated Name",
            connector_type=ConnectorType.LOCAL_FILE,
            configuration={},
            schedule_type=ScheduleType.MANUAL,
            status=ConnectorStatus.IDLE,
            total_docs_count=0,
            is_enabled=True,
        )

        mock_conn_svc.update_connector.return_value = mock_response
        response = client.put(f"/api/v1/connectors/{conn_id}", json=data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_scan_connector_files(self):
        from app.schemas.connector import ConnectorResponse
        from app.schemas.enums import ConnectorStatus, ConnectorType, ScheduleType

        conn_id = uuid4()
        mock_response = ConnectorResponse(
            id=conn_id,
            name="Test",
            connector_type=ConnectorType.LOCAL_FOLDER,
            configuration={},
            schedule_type=ScheduleType.MANUAL,
            status=ConnectorStatus.SYNCING,
            total_docs_count=0,
            is_enabled=True,
        )

        mock_conn_svc.scan_connector.return_value = mock_response
        response = client.post(f"/api/v1/connectors/{conn_id}/scan-files")
        assert response.status_code == 200
        mock_conn_svc.scan_connector.assert_called_once_with(conn_id)

    def test_stop_connector(self):
        from app.schemas.connector import ConnectorResponse
        from app.schemas.enums import ConnectorStatus, ConnectorType, ScheduleType

        conn_id = uuid4()
        mock_response = ConnectorResponse(
            id=conn_id,
            name="Test",
            connector_type=ConnectorType.LOCAL_FOLDER,
            configuration={},
            schedule_type=ScheduleType.MANUAL,
            status=ConnectorStatus.IDLE,
            total_docs_count=0,
            is_enabled=True,
        )

        mock_conn_svc.stop_connector.return_value = mock_response
        response = client.post(f"/api/v1/connectors/{conn_id}/stop")
        assert response.status_code == 200
        mock_conn_svc.stop_connector.assert_called_once_with(conn_id)

    @patch("app.services.chat.vanna_services.VannaServiceFactory", new_callable=AsyncMock)
    def test_train_vanna_connector_success(self, mock_vanna_factory):
        conn_id = uuid4()
        doc_id = uuid4()
        payload = {"document_ids": [str(doc_id)]}

        # Mock service return value
        mock_conn_svc.train_vanna.return_value = {"success": True, "trained_count": 1}

        response = client.post(f"/api/v1/connectors/{conn_id}/train", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["trained_count"] == 1

    def test_train_vanna_not_found(self):
        from app.core.exceptions import EntityNotFound

        conn_id = uuid4()
        # Mock service to raise EntityNotFound
        mock_conn_svc.train_vanna.side_effect = EntityNotFound("Connector not found")

        response = client.post(f"/api/v1/connectors/{conn_id}/train", json={"document_ids": [str(uuid4())]})
        # Expect 404
        assert response.status_code == 404
        assert response.json()["message"] == "Connector not found"

    def test_train_vanna_wrong_type(self):
        from app.core.exceptions import FunctionalError

        conn_id = uuid4()
        # Mock service to raise FunctionalError
        mock_conn_svc.train_vanna.side_effect = FunctionalError(
            message="only available for vanna_sql", error_code="INVALID_CONNECTOR_TYPE"
        )

        response = client.post(f"/api/v1/connectors/{conn_id}/train", json={"document_ids": [str(uuid4())]})
        # Expect 400
        assert response.status_code == 400
        assert "only available for vanna_sql" in response.json()["message"]

    def test_create_connector_document(self):
        from app.schemas.documents import ConnectorDocumentResponse
        from app.models.enums import DocStatus

        conn_id = uuid4()
        data = {"file_path": "test.txt", "file_name": "test.txt"}

        mock_response = ConnectorDocumentResponse(
            id=uuid4(),
            connector_id=conn_id,
            file_path="test.txt",
            file_name="test.txt",
            status=DocStatus.PENDING,
            doc_token_count=0,
            vector_point_count=0,
            processing_duration_ms=0.0,
            chunks_total=0,
            chunks_processed=0,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

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
        from app.schemas.documents import ConnectorDocumentResponse
        from app.models.enums import DocStatus

        conn_id = uuid4()
        doc_id = uuid4()
        data = {"file_name": "new_name.txt"}

        mock_response = ConnectorDocumentResponse(
            id=doc_id,
            connector_id=conn_id,
            file_path="test.txt",
            file_name="new_name.txt",
            status=DocStatus.PENDING,
            doc_token_count=0,
            vector_point_count=0,
            processing_duration_ms=0.0,
            chunks_total=0,
            chunks_processed=0,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

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
