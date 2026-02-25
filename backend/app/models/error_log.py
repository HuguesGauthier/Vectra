"""
Error logging model for application-wide error tracking.

SECURITY WARNING: This table stores error logs which may contain sensitive information.
Ensure proper access controls and data retention policies are in place.

ARCHITECT NOTE: Compliance Considerations
- Error messages and stack traces may contain PII or secrets
- Implement automatic sanitization before storage
- Define and enforce data retention policies (e.g., 30-90 days)
- Consider separate storage for high-sensitivity errors
- Ensure GDPR/CCPA compliance for user-associated logs
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import Column, DateTime, Index, Text, func
from sqlmodel import Field, SQLModel

# Validation constants
MAX_METHOD_LENGTH = 10  # HTTP methods are short (GET, POST, etc.)
MAX_PATH_LENGTH = 2048  # URL path limit
MAX_ERROR_MESSAGE_LENGTH = 5000  # Reasonable error message limit
MAX_STACK_TRACE_LENGTH = 50000  # Stack traces can be long but need limits

# HTTP status code ranges
MIN_STATUS_CODE = 100
MAX_STATUS_CODE = 599


class ErrorLog(SQLModel, table=True):
    """
    Application error log entry.

    Stores HTTP errors and exceptions for debugging and monitoring.

    SECURITY NOTES:
    - Stack traces may contain sensitive information (secrets, PII, file paths)
    - Error messages should be sanitized before storage
    - User IDs link errors to specific users (consent required)
    - Implement automatic cleanup after retention period

    ARCHITECT NOTE: Observability Pattern
    This table enables:
    - Error rate monitoring and alerting
    - User-specific error tracking
    - Debugging with full context
    - Security incident investigation

    Query Patterns:
    - Recent errors: ORDER BY timestamp DESC LIMIT 100
    - User errors: WHERE user_id = ? ORDER BY timestamp DESC
    - Error trends: GROUP BY DATE(timestamp), status_code
    """

    __tablename__ = "error_logs"
    model_config = {"validate_assignment": True}  # Pydantic V2

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), index=True  # Index for time-based queries
        ),
    )

    status_code: int = Field(
        nullable=False, ge=MIN_STATUS_CODE, le=MAX_STATUS_CODE, index=True  # Index for filtering by status
    )

    method: str = Field(nullable=False, max_length=MAX_METHOD_LENGTH)

    path: str = Field(nullable=False, max_length=MAX_PATH_LENGTH)

    error_message: str = Field(nullable=False, max_length=MAX_ERROR_MESSAGE_LENGTH)

    # Use max_length for Pydantic validation on input, though Text column supports unlimited.
    # Enforcing app constraint here is still good practice.
    stack_trace: str = Field(sa_column=Column(Text, nullable=False), max_length=MAX_STACK_TRACE_LENGTH)

    user_id: Optional[UUID] = Field(default=None, nullable=True, index=True)  # Index for user-specific queries

    # Additional table arguments for composite indexes
    __table_args__ = (
        # Composite index for common query pattern (recent errors by status)
        Index("ix_error_logs_timestamp_status", "timestamp", "status_code"),
    )

    @field_validator("method")
    @classmethod
    def validate_method_length(cls, v: str) -> str:
        if len(v) > MAX_METHOD_LENGTH:
            raise ValueError(f"Method too long (max {MAX_METHOD_LENGTH})")
        return v

    @field_validator("path", mode="before")
    @classmethod
    def validate_path_length(cls, v: str) -> str:
        if isinstance(v, str) and len(v) > MAX_PATH_LENGTH:
            # Truncate instead of raising error to avoid losing the log
            return v[:MAX_PATH_LENGTH]
        return v

    @field_validator("error_message", mode="before")
    @classmethod
    def validate_error_message_length(cls, v: str) -> str:
        if isinstance(v, str) and len(v) > MAX_ERROR_MESSAGE_LENGTH:
            # Truncate
            return v[:MAX_ERROR_MESSAGE_LENGTH]
        return v

    @field_validator("stack_trace", mode="before")
    @classmethod
    def validate_stack_trace_length(cls, v: str) -> str:
        if isinstance(v, str) and len(v) > MAX_STACK_TRACE_LENGTH:
            # Truncate
            return v[:MAX_STACK_TRACE_LENGTH]
        return v
