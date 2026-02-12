"""
Assistant Database Model.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.schemas.assistant import DEFAULT_INSTRUCTIONS, DEFAULT_TOP_K, DEFAULT_TOP_N, AIModel, AssistantBase

if TYPE_CHECKING:
    from .connector import Connector


# Many-to-Many Link
class AssistantConnectorLink(SQLModel, table=True):
    __tablename__ = "assistant_connectors"
    assistant_id: UUID = Field(sa_column=Column(ForeignKey("assistants.id", ondelete="CASCADE"), primary_key=True))
    connector_id: UUID = Field(sa_column=Column(ForeignKey("connectors.id", ondelete="CASCADE"), primary_key=True))


class Assistant(AssistantBase, table=True):
    """
    Database model for Assistants.
    Inherits schema/validation from AssistantBase in schemas/.
    """

    __tablename__ = "assistants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Overrides for Enums to match DB Keys (GPT_4O) to Python Enum
    model: AIModel = Field(
        sa_column=Column(Enum(AIModel, values_callable=lambda x: [e.value for e in x]), nullable=False)
    )

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

    # Avatar image filename (stored in assistant_avatars/ directory)
    avatar_image: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # Avatar vertical position (0-100)
    avatar_vertical_position: int = Field(
        default=50, sa_column=Column(Integer, server_default=text("50"), nullable=False)
    )

    # Re-applying sa_column because they were removed from AssistantBase for decoupling
    instructions: str = Field(default=DEFAULT_INSTRUCTIONS, sa_column=Column(Text, nullable=False))
    use_reranker: bool = Field(default=False, sa_column=Column(Boolean, server_default=text("false"), nullable=False))
    top_k_retrieval: int = Field(
        default=DEFAULT_TOP_K, sa_column=Column(Integer, server_default=text(str(DEFAULT_TOP_K)), nullable=False)
    )
    top_n_rerank: int = Field(
        default=DEFAULT_TOP_N, sa_column=Column(Integer, server_default=text(str(DEFAULT_TOP_N)), nullable=False)
    )
    similarity_cutoff: float = Field(default=0.25, sa_column=Column(Float, server_default=text("0.25"), nullable=False))
    retrieval_similarity_cutoff: float = Field(
        default=0.5, sa_column=Column(Float, server_default=text("0.5"), nullable=False)
    )

    # Semantic Caching
    use_semantic_cache: bool = Field(
        default=False, sa_column=Column(Boolean, server_default=text("false"), nullable=False)
    )
    cache_similarity_threshold: float = Field(
        default=0.90, sa_column=Column(Float, server_default=text("0.90"), nullable=False)
    )
    cache_ttl_seconds: int = Field(default=3600, sa_column=Column(Integer, server_default=text("3600"), nullable=False))
    user_authentication: bool = Field(
        default=False, sa_column=Column(Boolean, server_default=text("false"), nullable=False)
    )
    # The configuration is now a Pydantic model in the schema,
    # but we store it as JSONB in PG. SQLModel handles this conversion.
    configuration: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    linked_connectors: List["Connector"] = Relationship(
        link_model=AssistantConnectorLink, sa_relationship_kwargs={"lazy": "selectin"}
    )
