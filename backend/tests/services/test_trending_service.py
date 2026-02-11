import sys
from unittest.mock import MagicMock

# Mock pyodbc and vanna before any other imports to avoid ImportError in environments without them
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()
sys.modules["vanna.remote"] = MagicMock()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from app.services.trending_service import TrendingService
from app.models.topic_stat import TopicStat


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_vector_service():
    service = AsyncMock()
    service.get_async_qdrant_client = MagicMock()
    return service


@pytest.fixture
def mock_settings_service():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_repository, mock_vector_service, mock_settings_service):
    with patch("app.services.trending_service.VectorRepository") as mock_v_repo:
        svc = TrendingService(
            db=mock_db,
            repository=mock_repository,
            vector_service=mock_vector_service,
            settings_service=mock_settings_service,
        )
        svc.vector_repo = mock_v_repo.return_value
        return svc


@pytest.mark.asyncio
async def test_process_user_question_new_topic(service, mock_vector_service):
    # Setup
    a_id = uuid4()
    question = "How to use this app?"
    embedding = [0.1] * 1536

    # Mock semantic search results (empty for new topic)
    mock_client = mock_vector_service.get_async_qdrant_client.return_value
    mock_client.query_points = AsyncMock()
    mock_client.query_points.return_value.points = []

    # Execute
    await service.process_user_question(question, a_id, embedding)

    # Verify
    service.repository.create.assert_called_once()
    service.vector_repo.upsert_points.assert_called_once()


@pytest.mark.asyncio
async def test_process_user_question_existing_topic(service, mock_vector_service, mock_repository):
    # Setup
    a_id = uuid4()
    t_id = uuid4()
    question = "How to use this app?"
    embedding = [0.1] * 1536

    # Mock semantic search results (found match)
    mock_client = mock_vector_service.get_async_qdrant_client.return_value
    mock_client.query_points = AsyncMock()
    mock_match = MagicMock()
    mock_match.id = str(t_id)
    mock_match.score = 0.95
    mock_client.query_points.return_value.points = [mock_match]

    # Mock DB record
    mock_topic = MagicMock()
    mock_topic.frequency = 1
    mock_topic.raw_variations = ["How does it work?"]
    mock_repository.get_by_id_with_lock = AsyncMock(return_value=mock_topic)

    # Execute
    await service.process_user_question(question, a_id, embedding)

    # Verify
    assert mock_topic.frequency == 2
    assert question in mock_topic.raw_variations
    mock_db = service.db
    mock_db.commit.assert_called()


def test_clean_ai_title(service):
    titles = {
        "Titre : Ma super question": "Ma super question",
        '"A propos des prix"': "A propos des prix",
        "Suggestion : Comment ça marche ?": "Comment ça marche ?",
        "Simple question": "Simple question",
    }
    for raw, expected in titles.items():
        assert service._clean_ai_title(raw) == expected


@pytest.mark.asyncio
async def test_get_trending_topics_aggregation(service, mock_repository):
    # Setup
    a_id = uuid4()
    t1 = MagicMock(spec=TopicStat)
    t1.id = uuid4()
    t1.assistant_id = a_id
    t1.canonical_text = "Topic A"
    t1.frequency = 5
    t1.raw_variations = ["A1"]

    t2 = MagicMock(spec=TopicStat)
    t2.id = uuid4()
    t2.assistant_id = a_id
    t2.canonical_text = "Topic A "  # Duplicate with space
    t2.frequency = 3
    t2.raw_variations = ["A2"]

    t3 = MagicMock(spec=TopicStat)
    t3.id = uuid4()
    t3.assistant_id = a_id
    t3.canonical_text = "Topic B"
    t3.frequency = 10
    t3.raw_variations = ["B1"]

    mock_repository.get_trending = AsyncMock(return_value=[t1, t2, t3])

    # Execute
    results = await service.get_trending_topics(limit=5)

    # Verify
    assert len(results) == 2  # A and B
    assert results[0].canonical_text == "Topic B"  # Most frequent
    assert results[1].canonical_text == "Topic A"
    assert results[1].frequency == 8  # 5 + 3
