"""
Connector Database Model.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum, Integer, JSON, Text, func, text
from sqlmodel import Field, SQLModel

from app.schemas.connector import ConnectorBase
from app.models.enums import ConnectorStatus, ConnectorType, ScheduleType

# Validations constants needed for Field definitions if overriden,
# but here we rely on Base. Check MAX_* imports if needed.


class Connector(ConnectorBase, table=True):
    """
    Database model for Connectors.
    Inherits schema/validation from ConnectorBase in schemas/.
    """

    __tablename__ = "connectors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    status: ConnectorStatus = Field(
        default=ConnectorStatus.IDLE,
        sa_column=Column(Enum(ConnectorStatus, native_enum=False, values_callable=lambda x: [e.value for e in x])),
    )
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text))
    last_vectorized_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Explicit DB Columns (Moved from Schema)
    connector_type: ConnectorType = Field(
        sa_column=Column(Enum(ConnectorType, values_callable=lambda obj: [e.value for e in obj]))
    )
    # Note: JSON is standard SQL.

    configuration: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    schedule_type: Optional[ScheduleType] = Field(
        default=ScheduleType.MANUAL,
        sa_column=Column(Enum(ScheduleType, values_callable=lambda obj: [e.value for e in obj]), nullable=True),
    )

    # Chunking Config (Explicit DB defaults)
    chunk_size: int = Field(default=300, sa_column=Column(Integer, server_default=text("300"), nullable=False))
    chunk_overlap: int = Field(default=30, sa_column=Column(Integer, server_default=text("30"), nullable=False))

    total_docs_count: int = Field(default=0, ge=0)
    indexed_docs_count: int = Field(default=0, ge=0)
    failed_docs_count: int = Field(default=0, ge=0)

    last_sync_start_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    last_sync_end_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    created_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
