import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
import importlib
import app.services.connector_service

importlib.reload(app.services.connector_service)
from app.services.connector_service import ConnectorService
from app.schemas.enums import ConnectorType
from app.core.exceptions import TechnicalError


@pytest.mark.asyncio
class TestConnectorServiceTrain:
    async def test_train_vanna_success(self):
        # Mocks
        mock_repo = MagicMock()
        mock_scanner = MagicMock()
        mock_settings = MagicMock()
        service = ConnectorService(mock_repo, mock_scanner, settings_service=mock_settings)

        conn_id = uuid4()
        doc_id = uuid4()

        mock_connector = MagicMock()
        mock_connector.connector_type = ConnectorType.VANNA_SQL
        service.get_connector = AsyncMock(return_value=mock_connector)

        mock_doc_service = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.file_name = "test.sql"
        mock_doc.file_metadata = {"ddl": "CREATE TABLE ..."}
        mock_doc_service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)
        mock_doc_service.update_document = AsyncMock()

        with patch("app.services.chat.vanna_services.VannaServiceFactory", new_callable=AsyncMock) as mock_factory:
            mock_vanna = MagicMock()
            mock_factory.return_value = mock_vanna

            result = await service.train_vanna(conn_id, [doc_id], mock_doc_service)

            assert result["success"] is True
            assert result["trained_count"] == 1
            mock_doc_service.update_document.assert_called_once()
            args, _ = mock_doc_service.update_document.call_args
            assert args[1]["file_metadata"]["trained"] is True

    async def test_train_vanna_invalid_connector(self):
        mock_repo = MagicMock()
        mock_scanner = MagicMock()
        service = ConnectorService(mock_repo, mock_scanner)

        conn_id = uuid4()
        service.get_connector = AsyncMock(return_value=None)

        result = await service.train_vanna(conn_id, [uuid4()], MagicMock())
        assert result["success"] is False
        assert result["message"] == "Connector not found"

    async def test_train_vanna_wrong_type(self):
        mock_repo = MagicMock()
        mock_scanner = MagicMock()
        service = ConnectorService(mock_repo, mock_scanner)

        conn_id = uuid4()
        mock_connector = MagicMock()
        mock_connector.connector_type = ConnectorType.LOCAL_FILE
        service.get_connector = AsyncMock(return_value=mock_connector)

        result = await service.train_vanna(conn_id, [uuid4()], MagicMock())
        assert result["success"] is False
        assert "only available for vanna_sql" in result["message"]

    async def test_train_vanna_missing_ddl(self):
        mock_repo = MagicMock()
        mock_scanner = MagicMock()
        mock_settings = MagicMock()
        service = ConnectorService(mock_repo, mock_scanner, settings_service=mock_settings)

        conn_id = uuid4()
        doc_id = uuid4()

        mock_connector = MagicMock()
        mock_connector.connector_type = ConnectorType.VANNA_SQL
        service.get_connector = AsyncMock(return_value=mock_connector)

        mock_doc_service = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.file_metadata = {}  # Empty metadata
        mock_doc_service.document_repo.get_by_id = AsyncMock(return_value=mock_doc)

        with patch("app.services.chat.vanna_services.VannaServiceFactory", new_callable=AsyncMock) as mock_factory:
            mock_vanna = MagicMock()
            mock_factory.return_value = mock_vanna

            result = await service.train_vanna(conn_id, [doc_id], mock_doc_service)

            assert result["success"] is True
            assert result["trained_count"] == 0
            assert result["failed_count"] == 1
