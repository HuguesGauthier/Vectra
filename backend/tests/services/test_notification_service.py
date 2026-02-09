from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import EntityNotFound, TechnicalError
from app.models.enums import NotificationType
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    return NotificationService(mock_repo)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.mark.asyncio
async def test_get_notifications_secured(service, mock_repo, user_id):
    """Verify get_notifications passes user_id to repo and returns Pydantic models."""
    mock_notif = MagicMock()
    mock_notif.id = uuid4()
    mock_notif.user_id = user_id
    mock_notif.type = "info"
    mock_notif.message = "Hello"
    mock_notif.read = False
    mock_notif.created_at = datetime.now()

    # Repo returns list of ORM objects
    mock_repo.get_notifications.return_value = [mock_notif]

    result = await service.get_notifications(user_id=user_id, limit=10)

    # Check repo call
    mock_repo.get_notifications.assert_called_once_with(
        user_id=user_id, skip=0, limit=10, unread_only=False, notification_type=None
    )

    # Check return type
    assert len(result) == 1
    assert result[0].user_id == user_id
    assert result[0].message == "Hello"


@pytest.mark.asyncio
async def test_mark_as_read_secured_success(service, mock_repo, user_id):
    """Verify marking as read is scoped to user_id."""
    notif_id = uuid4()
    mock_notif = MagicMock()
    mock_notif.id = notif_id
    mock_notif.user_id = user_id
    mock_notif.read = False
    mock_notif.type = "info"
    mock_notif.message = "Msg"

    mock_repo.get_by_id_secured.return_value = mock_notif
    mock_repo.update.return_value = mock_notif

    await service.mark_notification_as_read(user_id=user_id, notification_id=notif_id)

    mock_repo.get_by_id_secured.assert_called_once_with(user_id, notif_id)
    assert mock_notif.read is True
    assert mock_repo.db.commit.called


@pytest.mark.asyncio
async def test_mark_as_read_secured_not_found(service, mock_repo, user_id):
    """Verify marking as read fails if notification doesn't belong to user."""
    notif_id = uuid4()
    mock_repo.get_by_id_secured.return_value = None

    with pytest.raises(EntityNotFound):
        await service.mark_notification_as_read(user_id=user_id, notification_id=notif_id)


@pytest.mark.asyncio
async def test_mark_all_as_read_requires_confirmation(service, user_id):
    """Verify bulk operation protection."""
    with pytest.raises(TechnicalError) as exc:
        await service.mark_all_as_read(user_id=user_id, user_confirmation=False)
    assert exc.value.error_code == "MISSING_CONFIRMATION"


@pytest.mark.asyncio
async def test_create_notification_success(service, mock_repo, user_id):
    """Verify creation sets user_id correctly."""
    data = NotificationCreate(user_id=user_id, type="info", message="Critical Error", read=False)

    mock_repo.create.side_effect = lambda x: (setattr(x, "id", uuid4()), x)[1]

    result = await service.create_notification(data)

    assert result.user_id == user_id
    assert result.message == "Critical Error"
    assert mock_repo.db.commit.called
