import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assistant import Assistant
from app.schemas.chat import Message
from app.services.cache_service import SemanticCacheService
from app.services.chat_history_service import ChatHistoryService
from app.services.settings_service import SettingsService
from app.services.vector_service import VectorService


class PipelineStepType(str, Enum):
    CACHE_LOOKUP = "cache_lookup"
    CACHE_UPDATE = "cache_update"
    RETRIEVAL = "retrieval"
    ASSISTANT_PERSISTENCE = "assistant_persistence"
    USER_PERSISTENCE = "user_persistence"
    TRENDING = "trending"
    COMPLETED = "completed"
    CONNECTION = "connection"
    ROUTER = "router"
    ROUTER_PROCESSING = "router_processing"
    ROUTER_RETRIEVAL = "router_retrieval"
    ROUTER_REASONING = "router_reasoning"
    SQL_SCHEMA_RETRIEVAL = "sql_schema_retrieval"
    ROUTER_SYNTHESIS = "router_synthesis"
    INITIALIZATION = "initialization"
    QUERY_EXECUTION = "query_execution"
    STREAMING = "streaming"
    HISTORY_LOADING = "history_loading"

    # Granular Agentic Steps
    ROUTER_SELECTION = "router_selection"
    SQL_GENERATION = "sql_generation"
    TOOL_EXECUTION = "tool_execution"
    VISUALIZATION_ANALYSIS = "visualization_analysis"

    # Standardized Types (Shared with Standard RAG)
    SYNTHESIS = "synthesis"
    VECTORIZATION = "vectorization"

    # CSV-Specific Steps
    AMBIGUITY_GUARD = "ambiguity_guard"
    CSV_SCHEMA_RETRIEVAL = "csv_schema_retrieval"
    CSV_SYNTHESIS = "csv_synthesis"
    FACET_QUERY = "facet_query"


class StepStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatMetrics(TypedDict):
    total_duration: float
    ttft: float
    step_breakdown: Dict[str, Any]
    input_tokens: int
    output_tokens: int
    step_token_breakdown: Dict[str, Dict[str, int]]


@dataclass
class ChatContext:
    # Request Data
    session_id: str
    message: str
    original_message: str
    assistant: Assistant
    language: str

    # Dependencies
    db: AsyncSession
    settings_service: SettingsService
    vector_service: VectorService
    chat_history_service: ChatHistoryService
    chat_history_service: ChatHistoryService
    cache_service: Optional[SemanticCacheService]
    query_engine_factory: Optional["UnifiedQueryEngineFactory"] = None

    # State flags
    should_stop: bool = False

    user_id: Optional[str] = None

    # Data Accumulators
    start_time: float = field(default_factory=time.time)
    history: List[Message] = field(default_factory=list)
    question_embedding: Optional[List[float]] = None
    captured_source_embedding: Optional[List[float]] = None
    full_response_text: str = ""
    retrieved_sources: List[Dict] = field(default_factory=list)
    sql_results: Optional[List] = None  # Raw SQL results (List[Tuple]) for visualization

    # Centralized Metrics Manager
    # We delay import to avoid circular dep if needed, or better, we import nicely
    # For now, we type as Any to allow import at top level without issues if metrics.py imports types.py
    # But metrics.py imports PipelineStepType from here. So we have circular dependency if we import metrics in types.
    # Solution: Use forward ref or TYPE_CHECKING.
    metrics: Any = field(default=None)  # ChatMetricsManager initialized in service

    step_timers: Dict = field(default_factory=dict)  # Legacy: usage to be removed progressively
    metadata: Dict = field(default_factory=dict)  # For storing pipeline-specific data (e.g., CSV decisions)

    # Flags
    trending_enabled: bool = False

    # Visualization Context
    visualization: Optional[Any] = None
