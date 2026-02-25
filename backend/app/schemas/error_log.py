from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel


class ErrorLogResponse(SQLModel):
    """
    Schema for error log response.

    ARCHITECT NOTE: Read-Only Schema
    Used for API responses. Excludes sensitive fields for security.
    Stack traces excluded by default - include only for admin users.
    """

    id: UUID
    timestamp: Optional[datetime] = None
    status_code: int
    method: str
    path: str
    error_message: str
    # Note: stack_trace excluded from default response for security
    # Note: user_id excluded for privacy
