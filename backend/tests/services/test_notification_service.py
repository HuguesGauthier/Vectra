import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationCreate
from app.core.exceptions import EntityNotFound, TechnicalError


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.db = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    return NotificationService(mock_repo)


def create_mock_notification(user_id, notif_id=None):
    mock_notif = MagicMock()
    mock_notif.id = notif_id or uuid4()
    mock_notif.user_id = user_id
    mock_notif.type = "info"
    mock_notif.message = "Test message"
    mock_notif.read = False
    mock_notif.created_at = None
    return mock_notif


@pytest.mark.asyncio
async def test_get_notifications_success(service, mock_repo):
    # Setup
    user_id = uuid4()
    mock_repo.get_notifications.return_value = [create_mock_notification(user_id)]

    # Execute
    result = await service.get_notifications(user_id=user_id)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    mock_repo.get_notifications.assert_called_once()


@pytest.mark.asyncio
async def test_create_notification_success(service, mock_repo):
    # Setup
    user_id = uuid4()
    notif_data = NotificationCreate(user_id=user_id, type="info", message="Test message", read=False)

    mock_repo.create.return_value = create_mock_notification(user_id)

    # Execute
    result = await service.create_notification(notif_data)

    # Assert
    assert result.message == "Test message"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_mark_as_read_success(service, mock_repo):
    # Setup
    user_id = uuid4()
    notif_id = uuid4()

    mock_notif = create_mock_notification(user_id, notif_id)
    mock_repo.get_by_id_secured.return_value = mock_notif

    # Mock update to return a "read" version
    read_notif = create_mock_notification(user_id, notif_id)
    read_notif.read = True
    mock_repo.update.return_value = read_notif

    # Execute
    result = await service.mark_notification_as_read(user_id, notif_id)

    # Assert
    assert result.read is True
    mock_repo.get_by_id_secured.assert_called_once_with(user_id, notif_id)
    mock_repo.update.assert_called_once_with(notif_id, {"read": True})


@pytest.mark.asyncio
async def test_bulk_operations_safety(service):
    # Setup
    user_id = uuid4()

    # Execute & Assert
    with pytest.raises(TechnicalError, match="requires confirmation"):
        await service.mark_all_as_read(user_id, user_confirmation=False)

    with pytest.raises(TechnicalError, match="requires confirmation"):
        await service.clear_all_notifications(user_id, user_confirmation=False)
