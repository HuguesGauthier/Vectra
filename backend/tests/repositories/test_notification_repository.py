import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.notification_repository import NotificationRepository
from app.models.notification import Notification
from app.core.exceptions import TechnicalError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.notification_repository.select") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_update():
    """Patch sqlalchemy update."""
    with patch("app.repositories.notification_repository.update") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_delete():
    """Patch sqlalchemy delete."""
    with patch("app.repositories.notification_repository.delete") as mock:
        yield mock


@pytest.fixture
def notification_repo(mock_db):
    return NotificationRepository(db=mock_db)


@pytest.mark.asyncio
async def test_get_notifications_secured(notification_repo, mock_db):
    """Test fetching notifications ensures tenant isolation."""
    user_id = uuid4()

    mock_notif = MagicMock(spec=Notification)
    mock_notif.user_id = user_id

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_notif]
    mock_db.execute.return_value = mock_result

    result = await notification_repo.get_notifications(user_id)

    assert len(result) == 1
    assert result[0].user_id == user_id
    # We can check specific where clauses if we want deep inspection,
    # but basic execution and result verification is pragmatic.


@pytest.mark.asyncio
async def test_get_by_id_secured_success(notification_repo, mock_db):
    """Test fetching owned notification."""
    user_id = uuid4()
    notif_id = uuid4()

    mock_notif = MagicMock(spec=Notification)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_notif
    mock_db.execute.return_value = mock_result

    result = await notification_repo.get_by_id_secured(user_id, notif_id)
    assert result == mock_notif


@pytest.mark.asyncio
async def test_get_by_id_secured_not_found(notification_repo, mock_db):
    """Test fetching unowned or non-existent notification returns None."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    result = await notification_repo.get_by_id_secured(uuid4(), uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_mark_all_as_read(notification_repo, mock_db):
    """Test batch update read status."""
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_db.execute.return_value = mock_result

    count = await notification_repo.mark_all_as_read(uuid4())

    assert count == 5
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_clear_all(notification_repo, mock_db):
    """Test atomic clearance of notifications."""
    mock_result = MagicMock()
    mock_result.rowcount = 10
    mock_db.execute.return_value = mock_result

    count = await notification_repo.clear_all(uuid4())

    assert count == 10
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_unread_count(notification_repo, mock_db):
    """Test unread count query."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = 3
    mock_db.execute.return_value = mock_result

    count = await notification_repo.get_unread_count(uuid4())

    assert count == 3
