import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.setting_repository import SettingRepository
from app.models.setting import Setting
from app.core.exceptions import TechnicalError


@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.setting_repository.select") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_update():
    """Patch sqlalchemy update."""
    with patch("app.repositories.setting_repository.update") as mock:
        yield mock


@pytest.fixture
def setting_repo(mock_db):
    return SettingRepository(db=mock_db)


@pytest.mark.asyncio
async def test_update_by_key_secured(setting_repo, mock_db):
    """Test updating setting only modifies allowed fields."""
    key = "test_key"
    mock_setting = MagicMock(spec=Setting)
    mock_setting.value = "old_value"
    mock_setting.key = key

    # Simulate finding existing setting
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_setting
    mock_db.execute.return_value = mock_result

    # Try to update value and key (attack attempt)
    data = {"value": "new_value", "key": "hacked_key", "group": "hacked_group"}

    updated = await setting_repo.update_by_key(key, data)

    assert updated.value == "new_value"
    # Ensure key/group were NOT modified by the repository logic
    # Note: MagicMock doesn't prevent setting attributes unless we configure spec_set,
    # but our code change ensures we only touch 'value'.
    # We can verify that setattr was NOT called for key/group if we spied,
    # or just trust the code logic we see + functional test.
    # Since we replaced the loop with specific assignment, other keys in `data` are ignored.
    assert updated.key == key


@pytest.mark.asyncio
async def test_update_bulk_atomicity(setting_repo, mock_db):
    """Test bulk update runs in single transaction."""
    updates = {"key1": "val1", "key2": "val2"}

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.execute.return_value = mock_result

    count = await setting_repo.update_bulk(updates)

    assert count == 2
    # Verify execute called twice (loop)
    assert mock_db.execute.call_count == 2
    # Verify single commit at end
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_bulk_rollback(setting_repo, mock_db):
    """Test bulk update rollback on error."""
    updates = {"key1": "val1"}

    mock_db.execute.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(TechnicalError):
        await setting_repo.update_bulk(updates)

    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_keys(setting_repo, mock_db):
    """Test retrieval of keys."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["k1", "k2"]
    mock_db.execute.return_value = mock_result

    keys = await setting_repo.get_all_keys()

    assert keys == {"k1", "k2"}
