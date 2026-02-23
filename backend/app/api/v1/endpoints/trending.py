import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import TechnicalError
from app.schemas.topic_stat import TopicStatResponse
from app.services.trending_service import TrendingService, get_trending_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[TopicStatResponse])
async def get_trending_topics(
    service: Annotated[TrendingService, Depends(get_trending_service)],
    assistant_id: Optional[UUID] = Query(None, description="Filter by Assistant ID."),
    limit: int = Query(10, ge=1, le=50, description="Max number of topics to return"),
) -> List[TopicStatResponse]:
    """
    Get top trending questions (semantic clusters).

    Args:
        service: The trending service instance.
        assistant_id: Optional UUID to filter by a specific assistant.
        limit: Maximum number of trending topics to return (1-50).

    Returns:
        List[TopicStatResponse]: A list of trending topics with their statistics.

    Raises:
        TechnicalError: If there's an error fetching the trending topics.
    """
    try:
        # Note: TrendingService.get_trending_topics already handles optional assistant_id
        # and will filter if provided.
        topics = await service.get_trending_topics(assistant_id=assistant_id, limit=limit)

        return topics

    except Exception as e:
        logger.error(f"❌ FAIL | get_trending_topics | Error: {str(e)}", exc_info=True)
        raise TechnicalError(f"Failed to fetch trending topics: {e}")
