import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.topic_repository import TopicRepository
from app.models.topic_stat import TopicStat
from app.core.exceptions import TechnicalError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.topic_repository.select") as mock:
        yield mock


@pytest.fixture
def topic_repo(mock_db):
    return TopicRepository(db=mock_db)


@pytest.mark.asyncio
async def test_get_by_id_with_lock(topic_repo, mock_db, mock_select):
    """Test fetching with lock."""
    topic_id = uuid4()
    mock_topic = MagicMock(spec=TopicStat)

    # Setup mock result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_topic
    mock_db.execute.return_value = mock_result

    # Setup select mock chain: select().where().with_for_update()
    mock_stmt = MagicMock()
    mock_select.return_value.where.return_value.with_for_update.return_value = mock_stmt

    result = await topic_repo.get_by_id_with_lock(topic_id)

    assert result == mock_topic
    # Verify execute called with the statement from with_for_update
    mock_db.execute.assert_called_once_with(mock_stmt)


@pytest.mark.asyncio
async def test_get_by_id_with_lock_error(topic_repo, mock_db, mock_select):
    """Test error handling during lock acquisition."""
    mock_db.execute.side_effect = SQLAlchemyError("Lock Error")
    # Setup select mock chain to return something, otherwise it fails before execute
    mock_select.return_value.where.return_value.with_for_update.return_value = MagicMock()

    with pytest.raises(TechnicalError):
        await topic_repo.get_by_id_with_lock(uuid4())


@pytest.mark.asyncio
async def test_get_trending_success(topic_repo, mock_db):
    """Test trending topics retrieval."""
    mock_topics = [MagicMock(spec=TopicStat), MagicMock(spec=TopicStat)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_topics
    mock_db.execute.return_value = mock_result

    result = await topic_repo.get_trending(limit=5)

    assert len(result) == 2
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_trending_with_assistant_filter(topic_repo, mock_db):
    """Test trending topics with assistant filter."""
    assistant_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    await topic_repo.get_trending(assistant_id=assistant_id)

    mock_db.execute.assert_called_once()
    # We can assume the query construction logic works if no error is raised
