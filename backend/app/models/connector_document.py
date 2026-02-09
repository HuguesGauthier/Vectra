"""
Connector Document Model.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel

from app.schemas.documents import ConnectorDocumentBase


class ConnectorDocument(ConnectorDocumentBase, table=True):
    """
    Database model for Connector Documents.
    Inherits schema/validation from ConnectorDocumentBase in schemas/.
    """

    __tablename__ = "connectors_documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    connector_id: UUID = Field(index=True, foreign_key="connectors.id", nullable=False)

    created_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    __table_args__ = (UniqueConstraint("connector_id", "file_path", name="uq_connector_file_path"),)
