import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.repositories.chat_history_repository import ChatRedisRepository
from app.schemas.chat import MAX_CONTENT_LENGTH, Message, MessageRole

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """
    Service to manage sliding window conversation history.
    Business layer over Redis Hot Storage.
    """

    def __init__(self, repository: ChatRedisRepository):
        self.repository = repository

    async def add_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to the sliding window history.
        Enforces validation and serialization.
        """
        if not session_id or not content:
            return

        # P0: Security & Validation (DoS Protection)
        if len(content) > MAX_CONTENT_LENGTH:
            logger.warning(f"Truncating massive message in session {session_id} ({len(content)} chars)")
            content = content[:MAX_CONTENT_LENGTH]

        message_data = {"role": role, "content": content}

        if metadata:
            message_data["metadata"] = metadata

        await self.repository.push_message(session_id, message_data)

    async def get_history(self, session_id: str) -> List[Message]:
        """
        Retrieve current sliding window history.
        Implements Fallback Strategy: Redis (Hot) -> Postgres (Cold).
        """
        # 1. Try Hot Storage (Redis)
        raw_items = await self.repository.get_recent_messages(session_id)

        # 2. Fallback: If Redis is empty, try Cold Storage (Postgres)
        if not raw_items:
            logger.info(f"❄️ Redis empty for {session_id}. Attempting Cold Storage fallback...")
            from app.core.database import SessionLocal
            from app.repositories.chat_history_repository import \
                ChatPostgresRepository

            try:
                # Create a temporary DB session for this specific fallback operation
                # We don't injection ChatPostgresRepository directly to avoid overhead on every request
                async with SessionLocal() as db:
                    cold_repo = ChatPostgresRepository(db)
                    raw_items = await cold_repo.get_last_n_messages(session_id, limit=self.repository.WINDOW_SIZE)

                if raw_items:
                    logger.info(f"🔥 Re-hydrating Redis with {len(raw_items)} messages from Cold Storage")
                    # Warmup Redis to prevent repeating this DB hit
                    await self.repository.push_messages(session_id, raw_items)
                else:
                    logger.debug(f"∅ No history in Cold Storage either for {session_id}")

            except Exception as e:
                logger.error(f"Fallback failed for {session_id}: {e}")
                # Fail gracefully, return empty history
                raw_items = []

        valid_messages = []
        for item in raw_items:
            try:
                # P2: Strict Typing
                valid_messages.append(Message(**item))
            except Exception as e:
                logger.warning(f"Skipping invalid history item in {session_id}: {e}")

        return valid_messages

    async def clear_history(self, session_id: str) -> None:
        """Clear history for a session."""
        await self.repository.clear(session_id)


from typing import Annotated

# -------------------------------------------------------------
# Dependency Injection
# -------------------------------------------------------------
from fastapi import Depends
from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

from app.core.settings import settings

# P1: Singleton Pattern (Connection Pooling)
_redis_client: Optional[Redis] = None
_redis_lock = asyncio.Lock()


async def get_redis_client() -> Redis:
    """
    Get or create a strict Singleton Redis client.
    Reuses the internal connection pool across requests.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    async with _redis_lock:
        if _redis_client is None:
            logger.info("⚡ Initializing Global Redis Connection Pool...")
            redis_url = (
                f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            )
            # decode_responses=True ensures we get str not bytes
            _redis_client = redis_from_url(redis_url, decode_responses=True)

    return _redis_client


async def shutdown_redis():
    """Closes the Redis connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def get_chat_history_repository() -> ChatRedisRepository:
    """Dependency provider."""
    redis = await get_redis_client()
    return ChatRedisRepository(redis)


async def get_chat_history_service(
    repository: Annotated[ChatRedisRepository, Depends(get_chat_history_repository)],
) -> ChatHistoryService:
    """Dependency provider."""
    return ChatHistoryService(repository)
