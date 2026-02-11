import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.connector_state_service import ConnectorStateService
from app.schemas.enums import ConnectorStatus, DocStatus, ConnectorType
from app.models.connector import Connector

# --- Fixtures ---

@pytest.fixture
def mock_deps():
    return {
        "db": AsyncMock(),
        "clock": MagicMock(),
    }

@pytest.fixture
def state_service(mock_deps):
    # We mock the repositories that are initialized in __init__
    with patch("app.services.connector_state_service.ConnectorRepository", return_value=AsyncMock()) as mock_crepo, \
         patch("app.services.connector_state_service.DocumentRepository", return_value=AsyncMock()) as mock_drepo:
        service = ConnectorStateService(db=mock_deps["db"], clock=mock_deps["clock"])
        service.connector_repo = mock_crepo.return_value
        service.doc_repo = mock_drepo.return_value
        return service

@pytest.fixture
def mock_ws_manager():
    with patch("app.services.connector_state_service.manager") as manager_mock:
        manager_mock.emit_connector_status = AsyncMock()
        manager_mock.emit_connector_updated = AsyncMock()
        manager_mock.emit_document_update = AsyncMock()
        yield manager_mock

# --- Tests ---

@pytest.mark.asyncio
async def test_finalize_connector_flow(state_service, mock_deps, mock_ws_manager):
    """Happy Path: Finalize connector correctly updates stats and emits events."""
    connector_id = uuid4()
    now = datetime.datetime.now(datetime.UTC)
    mock_deps["clock"].utcnow.return_value = now
    
    # Mocking doc count
    state_service.doc_repo.count_by_connector.return_value = 42
    
    # Mocking repo update to return a valid connector for Pydantic validation
    fake_connector = Connector(
        id=connector_id,
        name="Test",
        status=ConnectorStatus.IDLE,
        connector_type=ConnectorType.LOCAL_FILE,
        last_vectorized_at=now,
        total_docs_count=42
    )
    state_service.connector_repo.update.return_value = fake_connector
    
    # Act
    await state_service.finalize_connector(connector_id)
    
    # Assert
    state_service.doc_repo.count_by_connector.assert_awaited_once_with(connector_id)
    state_service.connector_repo.update.assert_awaited_once()
    
    # Verify emissions
    mock_ws_manager.emit_connector_status.assert_awaited_with(connector_id, ConnectorStatus.IDLE)
    mock_ws_manager.emit_connector_updated.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_connector_failed_persistence(state_service, mock_ws_manager):
    """Worst Case: Verify that failure state and error message are persisted."""
    connector_id = uuid4()
    error_msg = "Critical disk failure"
    
    # Act
    await state_service.mark_connector_failed(connector_id, error_msg)
    
    # Assert
    state_service.connector_repo.update.assert_awaited_once_with(
        connector_id, {"status": ConnectorStatus.ERROR, "last_error": error_msg}
    )
    mock_ws_manager.emit_connector_status.assert_awaited_with(connector_id, ConnectorStatus.ERROR)
