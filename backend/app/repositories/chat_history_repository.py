import json
import logging
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.exceptions import TechnicalError

logger = logging.getLogger(__name__)


class ChatRedisRepository:
    """
    Repository for accessing Chat History in Redis (Hot Storage).
    Handles Context Window (Sliding Window).
    """

    WINDOW_SIZE = 10
    TTL_SECONDS = 3600
    KEY_PREFIX = "chat_history:"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def _get_key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}{session_id}"

    async def push_message(self, session_id: str, message_data: Dict[str, Any]) -> None:
        """
        Atomic Push + Trim + Expire.
        """
        if not session_id or not message_data:
            return

        key = self._get_key(session_id)

        try:
            message_json = json.dumps(message_data)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message for Redis: {e}")
            return

        try:
            async with self.redis.pipeline() as pipe:
                pipe.rpush(key, message_json)
                pipe.ltrim(key, -self.WINDOW_SIZE, -1)
                pipe.expire(key, self.TTL_SECONDS)
                await pipe.execute()
        except Exception as e:
            logger.error(f"Redis write failed for session {session_id}: {e}")

    async def get_recent_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the current sliding window.
        """
        key = self._get_key(session_id)
        try:
            raw_items = await self.redis.lrange(key, 0, -1)
            history = []
            for item in raw_items:
                try:
                    if isinstance(item, bytes):
                        item = item.decode("utf-8")
                    history.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping malformed history item in {session_id}")
            return history
        except Exception as e:
            logger.error(f"Redis read failed for session {session_id}: {e}")
            return []

    async def clear(self, session_id: str) -> None:
        """Clear Redis history."""
        key = self._get_key(session_id)
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis clear failed for session {session_id}: {e}")


from app.models.chat_history import ChatHistory


class ChatPostgresRepository:
    """
    Repository for Chat Audit Logs in PostgreSQL (Cold Storage).
    Replaced raw SQL with `ChatHistory` ORM model.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        assistant_id: Optional[UUID] = None,
        user_id: Optional[str] = None,
        additional_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Persist message to Postgres for Audit/Analytics.
        """
        try:
            entry = ChatHistory(
                session_id=session_id,
                role=role,
                content=content,
                assistant_id=assistant_id,
                user_id=user_id,
                metadata_=additional_kwargs or {},
            )
            self.db.add(entry)
            await self.db.commit()

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to save message audit for {session_id}: {e}")

    async def get_messages(self, session_id: str) -> List[ChatHistory]:
        """Retrieve full conversation history for a session."""
        try:
            stmt = (
                select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.created_at.asc())
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to fetch audit history for {session_id}: {e}")
            return []

    async def clear_history(self, session_id: str) -> bool:
        """Clear Postgres history (e.g. for hard reset)."""
        try:
            stmt = text("DELETE FROM chat_history WHERE session_id = :session_id")
            result = await self.db.execute(stmt, {"session_id": session_id})
            await self.db.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to clear audit history for {session_id}: {e}")
            raise TechnicalError(f"Database error: {e}")

    async def purge_old_messages(self, retention_days: int) -> int:
        """
        Delete messages older than X days.
        Returns count of deleted messages.
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            stmt = delete(ChatHistory).where(ChatHistory.created_at < cutoff_date)
            result = await self.db.execute(stmt)
            await self.db.commit()

            count = result.rowcount
            if count > 0:
                logger.info(f"🧹 Purged {count} old chat history records (older than {retention_days} days)")
            return count
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to purge old history: {e}")
            return 0

    async def get_last_n_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the last N messages for a session (for Context Restoration).
        Returns list of dicts compatible with Message schema.
        """
        try:
            # Get last N messages (descending), then reverse to chronological order
            stmt = (
                select(ChatHistory)
                .where(ChatHistory.session_id == session_id)
                .order_by(ChatHistory.created_at.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            # Convert to Message-compatible dicts and reverse list to be chronological
            history = []
            for row in reversed(rows):
                history.append(
                    {
                        "role": row.role,
                        "content": row.content,
                        # We could include metadata here if needed
                    }
                )
            return history
        except Exception as e:
            logger.error(f"Failed to fetch fallback history for {session_id}: {e}")
            return []


async def get_chat_postgres_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ChatPostgresRepository:
    return ChatPostgresRepository(db)
