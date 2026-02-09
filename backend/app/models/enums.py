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
