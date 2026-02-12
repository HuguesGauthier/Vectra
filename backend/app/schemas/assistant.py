"""
Assistant Schemas - Pydantic definitions for API request/response.

ARCHITECT NOTE: Schema-Model Separation
We define the Pydantic schemas here to decouple API validation logic from
Database Table logic, complying with Clean Architecture.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, ValidationInfo, field_validator
from sqlmodel import SQLModel

# --- Enums ---


class AIModel(StrEnum):
    GEMINI = "gemini"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    OPENAI = "openai"
    MISTRAL = "mistral"
    OLLAMA = "ollama"


# --- Configuration Constants ---
DEFAULT_INSTRUCTIONS = "You are a helpful assistant."
DEFAULT_MODEL = AIModel.GPT_4O
DEFAULT_AVATAR_COLOR = "primary"
DEFAULT_AVATAR_TEXT_COLOR = "white"
DEFAULT_TOP_K = 25
DEFAULT_TOP_N = 5

# Validation constraints
MIN_TOP_K = 1
MAX_TOP_K = 100
MIN_TOP_N = 1
MAX_TOP_N = 50
MAX_CONNECTORS = 100  # DoS Protection


class AssistantConfig(SQLModel):
    """Structured configuration for Assistant internal settings."""

    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=4096, ge=1, le=8192)
    tags: Optional[List[str]] = Field(default_factory=list)  # ACL tags


class AssistantBase(SQLModel):
    """
    Base properties for Assistant.
    Contains all shared fields and validation logic.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    avatar_bg_color: str = Field(default=DEFAULT_AVATAR_COLOR, max_length=50)
    avatar_text_color: str = Field(default=DEFAULT_AVATAR_TEXT_COLOR, max_length=50)
    avatar_image: Optional[str] = Field(default=None, max_length=255)
    avatar_vertical_position: int = Field(default=50, ge=0, le=100)

    instructions: str = Field(default=DEFAULT_INSTRUCTIONS, min_length=1)
    model: AIModel = Field(default=DEFAULT_MODEL)

    use_reranker: bool = Field(default=False)

    top_k_retrieval: int = Field(default=DEFAULT_TOP_K, ge=MIN_TOP_K, le=MAX_TOP_K)
    top_n_rerank: int = Field(default=DEFAULT_TOP_N, ge=MIN_TOP_N, le=MAX_TOP_N)

    # New: Vector Similarity Cutoff (0.0 - 1.0)
    retrieval_similarity_cutoff: float = Field(default=0.5, ge=0.0, le=1.0)

    # New: Minimum similarity score (0.0 - 1.0) to keep a document
    similarity_cutoff: float = Field(default=0.5, ge=0.0, le=1.0)

    # Semantic Caching
    use_semantic_cache: bool = Field(default=False)
    cache_similarity_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    cache_ttl_seconds: int = Field(default=3600, ge=1)

    user_authentication: bool = Field(default=False)
    configuration: AssistantConfig = Field(default_factory=AssistantConfig)
    is_enabled: bool = Field(default=True)

    @property
    def model_provider(self) -> str:
        """Derive provider from model enum."""
        m = self.model.value if hasattr(self.model, "value") else str(self.model)
        m = m.lower()
        if "gemini" in m:
            return "gemini"
        if "openai" in m or "gpt" in m:
            return "openai"
        if "mistral" in m:
            return "mistral"
        if "ollama" in m:
            return "ollama"
        if "local" in m or "llama" in m:
            return "local"
        return "gemini"  # Default fallback

    # --- Validators ---

    @field_validator("top_n_rerank")
    @classmethod
    def validate_top_n(cls, v: int, info: ValidationInfo) -> int:
        """Ensure top_n <= top_k to avoid logic errors."""
        values = info.data
        if "top_k_retrieval" in values and v > values["top_k_retrieval"]:
            raise ValueError(f"top_n_rerank ({v}) cannot be > top_k_retrieval ({values['top_k_retrieval']})")
        return v


class AssistantCreate(AssistantBase):
    """Schema for Creation."""

    linked_connector_ids: List[UUID] = Field(default_factory=list, max_length=MAX_CONNECTORS)  # P0: DoS Protection


class AssistantUpdate(SQLModel):
    """Schema for Updates (Patch)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    avatar_bg_color: Optional[str] = Field(None, max_length=50)
    avatar_text_color: Optional[str] = Field(None, max_length=50)
    avatar_image: Optional[str] = Field(None, max_length=255)
    avatar_vertical_position: Optional[int] = Field(None, ge=0, le=100)
    instructions: Optional[str] = Field(None, min_length=1)
    model: Optional[AIModel] = None
    use_reranker: Optional[bool] = None
    top_k_retrieval: Optional[int] = Field(None, ge=MIN_TOP_K, le=MAX_TOP_K)
    top_n_rerank: Optional[int] = Field(None, ge=MIN_TOP_N, le=MAX_TOP_N)
    retrieval_similarity_cutoff: Optional[float] = Field(None, ge=0.0, le=1.0)
    similarity_cutoff: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Semantic Caching
    use_semantic_cache: Optional[bool] = None
    cache_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    cache_ttl_seconds: Optional[int] = Field(None, ge=1)

    user_authentication: Optional[bool] = None
    configuration: Optional[AssistantConfig] = None
    is_enabled: Optional[bool] = None
    linked_connector_ids: Optional[List[UUID]] = Field(None, max_length=MAX_CONNECTORS)

    @field_validator("top_n_rerank")
    @classmethod
    def validate_top_n_update(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        if v is None:
            return v
        values = info.data
        if "top_k_retrieval" in values and values["top_k_retrieval"] is not None:
            if v > values["top_k_retrieval"]:
                raise ValueError(f"top_n_rerank cannot be > top_k_retrieval")
        return v


class ConnectorRef(SQLModel):
    """Minimal Connector representation."""

    id: UUID
    name: str


class AssistantResponse(AssistantBase):
    """Schema for Responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    linked_connectors: List[ConnectorRef] = Field(default_factory=list)
