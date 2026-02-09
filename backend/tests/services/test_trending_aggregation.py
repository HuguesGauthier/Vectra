from typing import List
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.topic_stat import TopicStat
from app.services.trending_service import TrendingService


# Mock dependencies
@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_repo):
    return TrendingService(
        db=MagicMock(), repository=mock_repo, vector_service=MagicMock(), settings_service=MagicMock()
    )


def make_topic(text: str, freq: int) -> TopicStat:
    return TopicStat(id=uuid4(), canonical_text=text, frequency=freq, assistant_id=uuid4(), raw_variations=[text])


@pytest.mark.asyncio
async def test_get_trending_topics_aggregates_duplicates(service, mock_repo):
    """
    Test that duplicate canonical_text entries are aggregated.
    Scenario:
    - "A": freq 5
    - "A": freq 3
    - "B": freq 2

    Expected:
    - "A": freq 8
    - "B": freq 2
    """
    # Arrange
    raw_data = [
        make_topic("Topic A", 5),
        make_topic("Topic A", 3),
        make_topic("Topic B", 2),
    ]
    mock_repo.get_trending.return_value = raw_data

    # Act
    results = await service.get_trending_topics(limit=5)

    # Assert
    assert len(results) == 2

    # Results should be sorted by frequency DESC
    first = results[0]
    second = results[1]

    assert first.canonical_text == "Topic A"
    assert first.frequency == 8

    assert second.canonical_text == "Topic B"
    assert second.frequency == 2

    # Verify we fetched more than limit (the implementation fetches limit * 5)
    # limit passed was 5, so we expect get_trending called with 25
    mock_repo.get_trending.assert_called_with(None, 25)


@pytest.mark.asyncio
async def test_get_trending_topics_merges_variations(service, mock_repo):
    """
    Test that raw_variations are merged.
    """
    # Arrange
    t1 = make_topic("Topic A", 1)
    t1.raw_variations = ["Var 1"]

    t2 = make_topic("Topic A", 1)
    t2.raw_variations = ["Var 2"]

    mock_repo.get_trending.return_value = [t1, t2]

    # Act
    results = await service.get_trending_topics(limit=5)

    # Assert
    assert len(results) == 1
    aggregated = results[0]
    assert aggregated.frequency == 2
    assert "Var 1" in aggregated.raw_variations
    assert "Var 2" in aggregated.raw_variations


@pytest.mark.asyncio
async def test_get_trending_topics_filters_low_frequency(service, mock_repo):
    """
    Test that topics with frequency < 2 are filtered out.
    """
    # Arrange
    t1 = make_topic("Popular", 5)
    t2 = make_topic("Rare", 1)

    mock_repo.get_trending.return_value = [t1, t2]

    # Act
    results = await service.get_trending_topics(limit=5)

    # Assert
    assert len(results) == 1
    assert results[0].canonical_text == "Popular"
