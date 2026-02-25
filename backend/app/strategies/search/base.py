"""
Search Strategy Base - Abstract interface for search/RAG strategies.

Defines the contract for different search approaches (vector-only, hybrid, etc.).
Hardened for production with strict typing, validation, and observability.
"""

import logging
from abc import ABC, abstractmethod
from typing import Annotated, Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# Configuration constants
MAX_TOP_K = 100
DEFAULT_TOP_K = 10
MAX_QUERY_LENGTH = 1000


class SearchFilters(BaseModel):
    """
    Validated search filters to prevent injection attacks.
    """

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields

    connector_id: Optional[UUID] = Field(default=None, description="Filter by connector ID")
    assistant: Optional[Any] = Field(default=None, description="Assistant object for multi-collection resolution")
    status: Optional[str] = Field(
        default=None, pattern="^(IDLE|PENDING|INDEXED|FAILED|UNSUPPORTED)$", description="Document status filter"
    )
    user_acl: Optional[list[str]] = Field(default=None, max_length=100, description="User access control list")

    @field_validator("user_acl")
    @classmethod
    def validate_acl(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Ensure ACL entries are safe."""
        if v:
            return [entry.strip()[:100] for entry in v if entry.strip()]
        return v


class SearchMetadata(BaseModel):
    """
    Validated metadata structure with size limits.
    """

    model_config = ConfigDict(extra="allow")  # Allow dynamic fields

    file_name: Optional[str] = Field(default=None, max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=1000)
    connector_name: Optional[str] = Field(default=None, max_length=255)
    created_at: Optional[str] = None  # ISO timestamp

    @model_validator(mode="before")
    @classmethod
    def limit_metadata_size(cls, data: Any) -> Any:
        """Prevent large metadata values."""
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str) and len(v) > 5000:
                    data[k] = v[:5000] + "...[truncated]"
        return data


class SearchResult(BaseModel):
    """
    Search result from vector database.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)  # Immutable for thread safety

    document_id: UUID
    score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Similarity score between 0 and 1")
    content: str = Field(..., min_length=1, max_length=100000, description="Document content")
    metadata: SearchMetadata = Field(default_factory=SearchMetadata, description="Document metadata")


class SearchStrategyError(Exception):
    """Base exception for search strategy errors."""

    pass


class SearchValidationError(SearchStrategyError):
    """Validation error in search parameters."""

    pass


class SearchExecutionError(SearchStrategyError):
    """Error during search execution."""

    pass


class SearchStrategy(ABC):
    """
    Abstract base class for search strategies.
    """

    def __init__(self):
        """Initialize strategy with logger."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def search(
        self,
        query: Annotated[str, Field(min_length=1, max_length=MAX_QUERY_LENGTH)],
        top_k: Annotated[int, Field(ge=1, le=MAX_TOP_K)] = DEFAULT_TOP_K,
        filters: Optional[SearchFilters] = None,
    ) -> list[SearchResult]:
        """
        Execute search with this strategy.

        Args:
            query: Search query text (1-1000 chars)
            top_k: Number of results to return (1-100)
            filters: Optional validated search filters

        Returns:
            List of validated search results
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass

    def _log_search_start(self, query: str, top_k: int) -> None:
        """Log search start."""
        self.logger.info(
            f"[{self.strategy_name}] Starting search",
            extra={"query_length": len(query), "top_k": top_k, "strategy": self.strategy_name},
        )

    def _log_search_complete(self, result_count: int, duration_ms: float) -> None:
        """Log search completion."""
        self.logger.info(
            f"[{self.strategy_name}] Search complete",
            extra={"result_count": result_count, "duration_ms": duration_ms, "strategy": self.strategy_name},
        )

    def _log_search_error(self, error: Exception) -> None:
        """Log search error."""
        self.logger.error(
            f"[{self.strategy_name}] Search failed",
            exc_info=True,
            extra={"error_type": type(error).__name__, "strategy": self.strategy_name},
        )
