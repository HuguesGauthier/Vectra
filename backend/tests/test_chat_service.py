import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure app is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.assistant import Assistant
from app.services.chat_service import ChatService


class TestChatService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mocks
        self.db = AsyncMock()
        self.vector_service = AsyncMock()
        self.settings_service = AsyncMock()
        self.chat_history_service = AsyncMock()
        self.query_engine_factory = AsyncMock()
        self.chat_repository = AsyncMock()
        self.cache_service = AsyncMock()

        self.service = ChatService(
            db=self.db,
            vector_service=self.vector_service,
            settings_service=self.settings_service,
            chat_history_service=self.chat_history_service,
            query_engine_factory=self.query_engine_factory,
            chat_repository=self.chat_repository,
            cache_service=self.cache_service,
            trending_service_enabled=True,
        )

    async def test_reset_conversation_success(self):
        session_id = "test-session"
        await self.service.reset_conversation(session_id)

        self.chat_history_service.clear_history.assert_called_once_with(session_id)
        self.chat_repository.clear_history.assert_called_once_with(session_id)

    async def test_reset_conversation_validation(self):
        with self.assertRaises(ValueError):
            await self.service.reset_conversation("")

    async def test_stream_chat_validation(self):
        assistant = MagicMock(spec=Assistant)
        # Empty message
        try:
            async for _ in self.service.stream_chat("", assistant, "session", "en"):
                pass
        except ValueError as e:
            self.assertEqual(str(e), "Message cannot be empty.")

        # Empty session
        try:
            async for _ in self.service.stream_chat("msg", assistant, "", "en"):
                pass
        except ValueError as e:
            self.assertEqual(str(e), "Session ID is required.")

    async def test_stream_chat_exception_handling(self):
        assistant = MagicMock(spec=Assistant)
        assistant.id = "test-id"
        self.db.execute.side_effect = Exception("DB Error")

        chunks = []
        async for chunk in self.service.stream_chat("msg", assistant, "session", "en"):
            chunks.append(chunk)

        self.assertTrue(len(chunks) > 0)
        error_response = json.loads(chunks[0])
        self.assertEqual(error_response["type"], "error")
        self.assertEqual(error_response["message"], "An unexpected error occurred. Please try again.")


if __name__ == "__main__":
    unittest.main()
