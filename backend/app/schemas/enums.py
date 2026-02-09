"""
Shared Enums for the application.
MOVED from models/enums.py to avoid circular imports.
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


class ConnectorType(StrEnum):
    LOCAL_FILE = "local_file"
    LOCAL_FOLDER = "local_folder"
    SQL = "sql"
    VANNA_SQL = "vanna_sql"


class ScheduleType(StrEnum):
    MANUAL = "manual"
    CRON = "cron"


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
