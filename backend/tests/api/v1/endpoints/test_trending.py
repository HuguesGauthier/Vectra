from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.trending import router
from app.models.topic_stat import TopicStatResponse
from app.services.trending_service import TrendingService, get_trending_service

# Mock Service Instance
mock_trending_svc = AsyncMock(spec=TrendingService)

# Setup App
app = FastAPI()
app.include_router(router, prefix="/api/v1/trends")


async def override_get_trending_service():
    return mock_trending_svc


app.dependency_overrides[get_trending_service] = override_get_trending_service

client = TestClient(app)


class TestTrending:

    def setup_method(self):
        mock_trending_svc.reset_mock()
        mock_trending_svc.get_trending_topics = AsyncMock()

    def test_get_trending_global(self):
        """Test getting global trends."""
        mock_response = [
            TopicStatResponse(
                id=uuid4(),
                canonical_text="How to reset password?",
                frequency=10,
                assistant_id=uuid4(),
                raw_variations=["Reset pass"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        mock_trending_svc.get_trending_topics.return_value = mock_response

        response = client.get("/api/v1/trends/")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["canonical_text"] == "How to reset password?"
        # Verify call using instance logic (no db passed)
        mock_trending_svc.get_trending_topics.assert_called_with(assistant_id=None, limit=10)

    def test_get_trending_assistant(self):
        """Test getting trends for specific assistant."""
        aid = uuid4()
        mock_trending_svc.get_trending_topics.return_value = []

        response = client.get(f"/api/v1/trends/?assistant_id={aid}&limit=20")

        assert response.status_code == 200
        mock_trending_svc.get_trending_topics.assert_called_with(assistant_id=aid, limit=20)
