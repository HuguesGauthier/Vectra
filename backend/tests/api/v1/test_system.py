from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.system import router
from app.core.security import get_current_admin, get_current_user
from app.models.user import User
from app.services.document_service import DocumentService, get_document_service
from app.services.system_service import SystemService, get_system_service

app = FastAPI()
app.include_router(router, prefix="/api/v1/system")

# Service Mocks
mock_system_svc = AsyncMock(spec=SystemService)
mock_doc_svc = AsyncMock(spec=DocumentService)


# Dependency Overrides
async def override_get_system_service():
    return mock_system_svc


async def override_get_document_service():
    return mock_doc_svc


def override_get_admin_user():
    return User(id=uuid4(), email="admin@test.com", is_superuser=True)


def override_get_normal_user():
    return User(id=uuid4(), email="user@test.com", is_superuser=False)


app.dependency_overrides[get_system_service] = override_get_system_service
app.dependency_overrides[get_document_service] = override_get_document_service
app.dependency_overrides[get_current_admin] = override_get_admin_user
app.dependency_overrides[get_current_user] = override_get_normal_user

# Use raise_server_exceptions=False to test 500 error responses
client = TestClient(app, raise_server_exceptions=False)


class TestSystem:

    def setup_method(self):
        mock_system_svc.reset_mock()
        mock_doc_svc.reset_mock()

    def test_open_file_success(self):
        """Test open-file delegates to SystemService and returns success."""
        mock_system_svc.open_file_by_document_id.return_value = True
        doc_id = str(uuid4())

        response = client.post("/api/v1/system/open-file", json={"document_id": doc_id})

        assert response.status_code == 200
        assert response.json() == {"message": "File opened", "success": True}
        mock_system_svc.open_file_by_document_id.assert_called_once_with(doc_id)

    def test_open_file_failure(self):
        """Test open-file handles exceptions."""
        mock_system_svc.open_file_by_document_id.side_effect = Exception("System error")
        doc_id = str(uuid4())

        response = client.post("/api/v1/system/open-file", json={"document_id": doc_id})

        assert response.status_code == 500
        mock_system_svc.open_file_by_document_id.assert_called_once_with(doc_id)

    def test_upload_file_success(self):
        """Test upload delegates to DocumentService."""
        mock_doc_svc.upload_file.return_value = "tmp/file.pdf"

        # Create dummy file content
        files = {"file": ("test.pdf", b"PDF_CONTENT", "application/pdf")}

        response = client.post("/api/v1/system/upload", files=files)

        assert response.status_code == 200
        assert response.json()["path"] == "tmp/file.pdf"
        mock_doc_svc.upload_file.assert_called_once()

    def test_upload_file_failure(self):
        """Test upload handles exceptions."""
        mock_doc_svc.upload_file.side_effect = Exception("Upload failed")
        files = {"file": ("test.pdf", b"PDF_CONTENT", "application/pdf")}

        response = client.post("/api/v1/system/upload", files=files)

        assert response.status_code == 500
        mock_doc_svc.upload_file.assert_called_once()

    def test_delete_temp_file_success(self):
        """Test delete_temp_file delegates to DocumentService."""
        mock_doc_svc.delete_temp_file.return_value = None
        temp_path = "tmp/file.pdf"

        # Using request() because delete() might not accept json in all versions of TestClient
        response = client.request("DELETE", "/api/v1/system/temp-file", json={"path": temp_path})

        assert response.status_code == 200
        assert response.json() == {"message": "File deleted successfully"}
        mock_doc_svc.delete_temp_file.assert_called_once_with(temp_path)

    def test_delete_temp_file_failure(self):
        """Test delete_temp_file handles exceptions."""
        mock_doc_svc.delete_temp_file.side_effect = Exception("Delete failed")
        temp_path = "tmp/file.pdf"

        response = client.request("DELETE", "/api/v1/system/temp-file", json={"path": temp_path})

        assert response.status_code == 500
        mock_doc_svc.delete_temp_file.assert_called_once_with(temp_path)
