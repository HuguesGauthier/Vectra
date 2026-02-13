from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from llama_index.core.schema import NodeWithScore, QueryBundle
from pydantic import BaseModel, ConfigDict


@dataclass
class PipelineContext:
    """Shared state for the request."""

    # Inputs
    user_message: str
    chat_history: List[Any]
    language: str
    assistant: Any

    # Dependencies (Injected)
    llm: Any
    embed_model: Any
    search_strategy: Any
    settings_service: Any = None
    tools: List[Any] = field(default_factory=list)

    # Intermediate State
    rewritten_query: Optional[str] = None
    query_bundle: Optional[QueryBundle] = None
    retrieved_nodes: List[NodeWithScore] = field(default_factory=list)
    response_stream: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PipelineEvent(BaseModel):
    """Standardized Event Emitted by Processors."""

    type: str  # "step", "sources", "response_stream", "error"
    step_type: Optional[str] = None  # "context", "vectorization", etc.
    status: Optional[str] = None  # "running", "completed"
    label: Optional[str] = None  # User-facing label override
    payload: Optional[Any] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
