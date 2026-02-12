import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.trending import get_trending_service
from app.models.topic_stat import TopicStat

# Mock Data
ASSISTANT_ID = uuid4()
TOPIC_ID = uuid4()

mock_topics = [
    TopicStat(
        id=TOPIC_ID,
        canonical_text="How to reset password?",
        frequency=10,
        assistant_id=ASSISTANT_ID,
        raw_variations=["password reset", "reset my pass"],
    )
]


@pytest.fixture
def client():
    app.dependency_overrides = {}
    return TestClient(app)


def test_get_trending_topics_happy_path(client):
    """Test successfully fetching trending topics."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_trending_topics.return_value = mock_topics
    app.dependency_overrides[get_trending_service] = lambda: mock_service

    response = client.get("/api/v1/trends/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["canonical_text"] == "How to reset password?"
    assert data[0]["frequency"] == 10


def test_get_trending_topics_with_filters(client):
    """Test fetching with assistant_id and limit filters."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_trending_topics.return_value = mock_topics
    app.dependency_overrides[get_trending_service] = lambda: mock_service

    url = f"/api/v1/trends/?assistant_id={ASSISTANT_ID}&limit=5"
    response = client.get(url)
    assert response.status_code == 200
    mock_service.get_trending_topics.assert_called_once_with(assistant_id=ASSISTANT_ID, limit=5)


def test_get_trending_topics_error(client):
    """Test error handling when service fails."""
    mock_service = pytest.importorskip("unittest.mock").AsyncMock()
    mock_service.get_trending_topics.side_effect = Exception("Database boom")
    app.dependency_overrides[get_trending_service] = lambda: mock_service

    response = client.get("/api/v1/trends/")
    assert response.status_code == 500
    data = response.json()
    assert data["code"] == "technical_error"
    assert "Failed to fetch trending topics" in data["message"]
