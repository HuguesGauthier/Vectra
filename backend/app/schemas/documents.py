"""
Document Schemas - Pydantic definitions for API request/response.

ARCHITECT NOTE: Schema-Model Separation
We define the Pydantic schemas here to decouple API validation logic from Database Table logic.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ConfigDict, ValidationInfo, field_validator
from sqlalchemy import Column, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.schemas.enums import DocStatus

# Validation constants
MAX_FILE_PATH_LENGTH = 2048
MAX_FILE_NAME_LENGTH = 255
MAX_HASH_LENGTH = 128
MAX_ERROR_MESSAGE_LENGTH = 2000
MAX_MIME_TYPE_LENGTH = 127


class ConnectorDocumentBase(SQLModel):
    """
    Base properties for Connector Document.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    # Note: connector_id is usually handled by the route/controller context,
    # but strictly speaking it belongs to the entity.
    # We make it Optional in Base because typically Create payloads might not define it
    # if nested under /connectors/{id}/documents. But if it's a flat list, it's needed.
    # In the model it was required. We'll keep it as field but might need handling in Create vs DB.
    # Actually, for Base used in DTOs, we often exclude FKs that are path parameters.
    # But usually Base mirrors the DB columns.

    file_path: str = Field(min_length=1, max_length=MAX_FILE_PATH_LENGTH)
    file_name: str = Field(min_length=1, max_length=MAX_FILE_NAME_LENGTH)

    last_modified_at_source: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    last_vectorized_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    file_size: Optional[int] = Field(default=None, ge=0)

    status: DocStatus = Field(
        default=DocStatus.PENDING,
        # We don't need sa_column here for Pydantic, but SQLModel uses it.
        # Ideally, we put sa_column in the DB model OR keep it here if we want
        # auto-generation of table columns from Base.
        # Given previous patterns, we keep sa_column here for SQLModel convenience.
        sa_column=Column(Enum(DocStatus, native_enum=False, values_callable=lambda x: [e.value for e in x])),
    )
    error_message: Optional[str] = Field(default=None, max_length=MAX_ERROR_MESSAGE_LENGTH)

    file_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    configuration: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    mime_type: Optional[str] = Field(default=None, max_length=MAX_MIME_TYPE_LENGTH)

    doc_token_count: Optional[int] = Field(default=None, ge=0)
    vector_point_count: Optional[int] = Field(default=None, ge=0)
    processing_duration_ms: Optional[float] = Field(default=None, ge=0.0)

    chunks_total: int = Field(default=0, ge=0)
    chunks_processed: int = Field(default=0, ge=0)

    # --- Validators ---

    # Validator removed per user request to prevent stability issues.

    @field_validator("file_metadata", "configuration")
    @classmethod
    def validate_metadata_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Prevent DoS via huge metadata objects."""
        try:
            txt = json.dumps(v)
            if len(txt) > 100_000:  # 100KB
                raise ValueError("Metadata/configuration too large (max 100KB)")
        except ValueError as e:
            raise e
        except Exception:
            raise ValueError("Invalid JSON structure")
        return v


class ConnectorDocumentCreate(SQLModel):
    """Schema for Creation."""

    file_path: str = Field(min_length=1, max_length=MAX_FILE_PATH_LENGTH)
    file_name: str = Field(min_length=1, max_length=MAX_FILE_NAME_LENGTH)
    file_size: Optional[int] = Field(None, ge=0)
    configuration: Optional[Dict[str, Any]] = None

    # Validation needed here because it doesn't inherit from Base directly
    # (Create payload is smaller than Base usually).
    # Or we can inherit Base and exclude fields.
    # Current existing schema was small. Let's keep it robust.

    @field_validator("configuration")
    @classmethod
    def validate_config(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v:
            return ConnectorDocumentBase.validate_metadata_size(v)
        return v


class ConnectorDocumentUpdate(SQLModel):
    """Schema for Partial Updates."""

    file_path: Optional[str] = Field(None, min_length=1, max_length=MAX_FILE_PATH_LENGTH)
    file_name: Optional[str] = Field(None, min_length=1, max_length=MAX_FILE_NAME_LENGTH)
    configuration: Optional[Dict[str, Any]] = None
    status: Optional[DocStatus] = None
    error_message: Optional[str] = Field(None, max_length=MAX_ERROR_MESSAGE_LENGTH)

    @field_validator("configuration")
    @classmethod
    def validate_config(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v:
            return ConnectorDocumentBase.validate_metadata_size(v)
        return v


class ConnectorDocumentResponse(ConnectorDocumentBase):
    """Schema for Response."""

    id: UUID
    connector_id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
