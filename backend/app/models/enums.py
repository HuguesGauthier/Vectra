"""
Shared Enums for the application.
"""

from enum import StrEnum


class ConnectorStatus(StrEnum):
    CREATED = "created"
    IDLE = "idle"
    QUEUED = "queued"
    SYNCING = "syncing"
    ERROR = "error"
    PAUSED = "paused"
    # Legacy statuses
    STARTING = "starting"
    VECTORIZING = "vectorizing"


class DocStatus(StrEnum):
    IDLE = "idle"
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PAUSED = "paused"
    UNSUPPORTED = "unsupported"


class NotificationType(StrEnum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"


class UserRole(StrEnum):
    """User Roles."""

    ADMIN = "admin"
    USER = "user"


class ConnectorType(StrEnum):
    LOCAL_FILE = "local_file"
    LOCAL_FOLDER = "local_folder"
    SQL = "sql"
    VANNA_SQL = "vanna_sql"


class ScheduleType(StrEnum):
    MANUAL = "manual"
    CRON = "cron"


class SettingGroup(StrEnum):
    """Allowed setting groups."""

    GENERAL = "general"
    AI = "ai"
    SYSTEM = "system"
    AUTH = "auth"
    STORAGE = "storage"
    NOTIFICATION = "notification"
