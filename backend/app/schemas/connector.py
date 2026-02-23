"""
Connector Schemas - Pydantic definitions for API request/response.

ARCHITECT NOTE: Schema-Model Separation
We define the Pydantic schemas here to decouple API validation logic from Database Table logic.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel

from app.schemas.enums import ConnectorStatus, ConnectorType, ScheduleType

# Validation constants
MAX_NAME_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 1000
MAX_CONNECTOR_TYPE_LENGTH = 100
MAX_ERROR_MESSAGE_LENGTH = 2000
MAX_CRON_LENGTH = 100


class IndexingConfig(SQLModel):
    """
    Configuration for smart metadata extraction during ingestion.
    Uses combo strategy: single LLM call extracts Title + Summary + Questions.
    """

    use_smart_extraction: bool = Field(
        default=False, description="Enable AI-powered metadata extraction (Title, Summary, Questions)"
    )
    extraction_model: str = Field(
        default="gemini-flash", description="LLM model for extraction. gemini-flash recommended for speed/cost."
    )


class ConnectorBase(SQLModel):
    """
    Base properties for Connector.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    description: Optional[str] = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    connector_type: ConnectorType
    configuration: Dict[str, Any] = Field(default_factory=dict)
    schedule_type: Optional[ScheduleType] = Field(default=ScheduleType.MANUAL)
    is_enabled: bool = Field(default=True)
    schedule_cron: Optional[str] = Field(default=None, max_length=MAX_CRON_LENGTH)

    # Chunking Configuration
    chunk_size: int = Field(default=300)
    chunk_overlap: int = Field(default=30)

    @property
    def indexing_config(self) -> IndexingConfig:
        """Parse indexing config from configuration dict."""
        config_data = self.configuration.get("indexing_config", {})
        return IndexingConfig(**config_data)

    # --- Validators ---

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron_syntax(cls, v: Optional[str]) -> Optional[str]:
        """Validate format of cron string."""
        if not v:
            return v

        # Basic field count check (5 or 6)
        fields = v.strip().split()
        if not (5 <= len(fields) <= 6):
            raise ValueError("Invalid cron: expected 5 or 6 fields")

        # Char check
        allowed = set("0123456789,-/*? ")
        if not all(c in allowed for c in v):
            raise ValueError("Invalid chars in cron")

        return v

    @field_validator("configuration")
    @classmethod
    def validate_configuration_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Prevent DoS via massive config blobs."""
        try:
            txt = json.dumps(v)
            if len(txt) > 100_000:  # 100KB
                raise ValueError("Configuration too large (max 100KB)")
        except ValueError as e:
            raise e
        except Exception:
            raise ValueError("Invalid JSON configuration")
        return v


class ConnectorCreate(ConnectorBase):
    """Schema for Creation."""

    pass


class ConnectorUpdate(SQLModel):
    """Schema for Partial Updates."""

    name: Optional[str] = Field(None, min_length=1, max_length=MAX_NAME_LENGTH)
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
    connector_type: Optional[ConnectorType] = None
    configuration: Optional[Dict[str, Any]] = None
    schedule_type: Optional[ScheduleType] = None
    is_enabled: Optional[bool] = None
    schedule_cron: Optional[str] = Field(None, max_length=MAX_CRON_LENGTH)

    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        return ConnectorBase.validate_cron_syntax(v)

    @field_validator("configuration")
    @classmethod
    def validate_config(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None:
            return ConnectorBase.validate_configuration_size(v)
        return v


class ConnectorResponse(ConnectorBase):
    """Schema for Responses."""

    id: UUID
    status: ConnectorStatus
    last_error: Optional[str] = None
    last_vectorized_at: Optional[datetime] = None
    total_docs_count: int = 0
    indexed_docs_count: int = 0
    failed_docs_count: int = 0
    last_sync_start_at: Optional[datetime] = None
    last_sync_end_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConnectorTestConnection(SQLModel):
    """Schema for Connection Testing."""

    connector_type: ConnectorType
    configuration: Dict[str, Any]


class ConnectorVannaTrain(SQLModel):
    """Schema for Vanna Training payload."""

    document_ids: List[UUID]
