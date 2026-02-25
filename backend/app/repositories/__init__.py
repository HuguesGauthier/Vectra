"""
Repository __init__.py - Export all repositories for easy imports.
"""

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.base_repository import BaseRepository
from app.repositories.chat_history_repository import ChatPostgresRepository, ChatRedisRepository
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.setting_repository import SettingRepository
from app.repositories.sql_repository import SQLRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vector_repository import VectorRepository

# Alias for convenience and consistency with other repositories
ChatHistoryRepository = ChatPostgresRepository

__all__ = [
    "BaseRepository",
    "SQLRepository",
    "UserRepository",
    "DocumentRepository",
    "VectorRepository",
    "AssistantRepository",
    "AnalyticsRepository",
    "ChatHistoryRepository",
    "ChatRedisRepository",
    "ChatPostgresRepository",
    "ConnectorRepository",
    "TopicRepository",
    "SettingRepository",
]
