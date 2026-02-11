import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from llama_index.core.callbacks.base import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.core.llms import ChatMessage

from app.services.chat.types import PipelineStepType
from app.services.chat.utils import EventFormatter

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Callback Handler that pushes LlamaIndex events to an asyncio Queue
    for streaming to the UI.
    """

    def __init__(self, queue: asyncio.Queue, language: str = "en"):
        self.queue = queue
        self.language = language
        self._event_map = {}  # Track context (step_type, label) by event_id
        self._event_starts = {}  # Fix: Restore event starts tracking
        self._has_used_tools = False
        self._is_sql_flow = False
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])

    def on_event_start(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Run when an event starts."""
        self._event_starts[event_id] = time.time()
        self._obs_event(event_type, "start", payload, event_id=event_id)
        return event_id

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Run when an event ends."""
        self._obs_event(event_type, "end", payload, event_id=event_id)

    def _obs_event(self, event_type: CBEventType, phase: str, payload: Optional[Dict] = None, event_id: str = ""):
        step_type = None
        label = None

        # Phase 1: Identification (Start Phase) OR Retrieval (End Phase)
        if phase == "start":
            # Heuristic Logic for Start
            if event_type == CBEventType.FUNCTION_CALL:
                step_type = PipelineStepType.TOOL_EXECUTION
                self._has_used_tools = True

            elif event_type == CBEventType.LLM:
                # ... (Existing identification logic) ...
                if self._has_used_tools:
                    step_type = PipelineStepType.ROUTER_SYNTHESIS
                else:
                    step_type = PipelineStepType.ROUTER_REASONING

                    is_sql = False
                    is_select = False

                    if payload and "messages" in payload:
                        messages = payload["messages"]
                        for msg in messages:
                            content = str(msg.content).lower()
                            if (
                                ("sql" in content and "table" in content)
                                or "postgresql" in content
                                or "select statement" in content
                            ):
                                is_sql = True
                                if "choices:" in content or "which tool" in content:
                                    is_sql = False
                                    is_select = True
                                break
                            if "choices:" in content or ("select" in content and "tool" in content):
                                is_select = True
                                break

                    if not is_sql and not is_select and payload and "serialized" in payload:
                        serialized = str(payload["serialized"])
                        if "NLSQLRetriever" in serialized or "SQL" in serialized:
                            is_sql = True
                        elif "Selector" in serialized:
                            is_select = True

                    if not is_sql and not is_select and payload and "template_vars" in payload:
                        t_vars = payload["template_vars"]
                        if isinstance(t_vars, dict):
                            if "choices" in t_vars and len(t_vars["choices"]) > 1:
                                is_select = True
                            elif "schema" in t_vars or "dialect" in t_vars:
                                is_sql = True

                    if is_sql:
                        step_type = PipelineStepType.SQL_GENERATION
                        self._is_sql_flow = True
                    elif is_select:
                        step_type = PipelineStepType.ROUTER_SELECTION

            elif event_type == CBEventType.RETRIEVE:
                step_type = PipelineStepType.RETRIEVAL

            elif event_type == CBEventType.AGENT_STEP:
                step_type = PipelineStepType.ROUTER_PROCESSING

            # Persist identification
            if step_type:
                self._event_map[event_id] = {"step_type": step_type, "label": label}

        else:
            # Phase 2: Recovery (End Phase)
            # Retrieve from map
            stored = self._event_map.pop(event_id, None)
            if stored:
                step_type = stored["step_type"]
                label = stored.get("label")
            else:
                # Fallback if map missing (orphan end event? shouldn't happen)
                return

        if not step_type:
            return

        # Calculate metrics if ending
        duration = None
        token_count = None

        if phase == "end":
            start_time = self._event_starts.pop(event_id, None)
            if start_time:
                duration = round(time.time() - start_time, 3)

            if payload:
                token_count = self._extract_usage_from_payload(payload)

        event_status = "running" if phase == "start" else "completed"

        # Build Payload for Frontend
        out_payload = {}
        if duration is not None:
            out_payload["duration"] = duration

        if token_count:
            out_payload["tokens"] = token_count
            # Accumulate tokens for later retrieval
            self.total_input_tokens += token_count.get("input", 0)
            self.total_output_tokens += token_count.get("output", 0)

        if step_type == PipelineStepType.RETRIEVAL:
            # Extract Node Count
            if payload and "nodes" in payload:
                nodes = payload["nodes"]
                out_payload["source_count"] = len(nodes)
            else:
                out_payload["source_count"] = 0

            # Hint if this is a SQL metadata retrieval
            # Check serialized hint OR the flow state
            if self._is_sql_flow:
                out_payload["is_sql"] = True
            elif payload and "serialized" in payload:
                serialized = str(payload["serialized"])
                # Fix: Require explicit SQL Retriever types, not just "Table" which might match File Table parsers
                if (
                    "NLSQLRetriever" in serialized
                    or "SQLRetriever" in serialized
                    or ("SQL" in serialized and "Table" in serialized)
                ):
                    out_payload["is_sql"] = True
                    self._is_sql_flow = True  # Persist for end phase or next retrievals

        # Dispatch raw event data for processor to handle (metrics & formatting)
        event_data = {
            "step_type": step_type,
            "status": event_status,
            "payload": out_payload,
            "duration": duration,
            "label": label,
        }

        try:
            self.queue.put_nowait(event_data)
        except asyncio.QueueFull:
            pass

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        pass

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        pass

    def _extract_usage_from_payload(self, payload: Dict) -> Optional[Dict]:
        """Robustly extract token usage from various LlamaIndex payload formats."""
        try:
            # 1. Direct 'usage' key (OpenAI style sometimes)
            if "usage" in payload and isinstance(payload["usage"], dict):
                return {
                    "input": payload["usage"].get("prompt_tokens", 0),
                    "output": payload["usage"].get("completion_tokens", 0),
                }

            # 2. Response Object Inspection
            if "response" in payload:
                resp = payload["response"]

                # A. Google Gemini (usage_metadata in raw)
                if hasattr(resp, "raw"):
                    # Handle Dict
                    if isinstance(resp.raw, dict):
                        usage_meta = resp.raw.get("usage_metadata")
                        if usage_meta:
                            return {
                                "input": usage_meta.get("prompt_token_count", 0),
                                "output": usage_meta.get("candidates_token_count", 0),
                            }
                    # Handle Object (google.generativeai.types.GenerateContentResponse)
                    elif hasattr(resp.raw, "usage_metadata"):
                        usage_meta = resp.raw.usage_metadata
                        # usage_meta might be object or dict
                        if hasattr(usage_meta, "prompt_token_count"):
                            return {
                                "input": getattr(usage_meta, "prompt_token_count", 0),
                                "output": getattr(usage_meta, "candidates_token_count", 0),
                            }
                        # Fallback if usage_metadata is dict-like but raw was object
                        elif isinstance(usage_meta, dict):
                            return {
                                "input": usage_meta.get("prompt_token_count", 0),
                                "output": usage_meta.get("candidates_token_count", 0),
                            }

                # B. Standard OpenAI / Generic
                usage = None
                if hasattr(resp, "raw") and isinstance(resp.raw, dict):
                    usage = resp.raw.get("usage")

                if not usage and hasattr(resp, "additional_kwargs"):
                    usage = resp.additional_kwargs.get("usage") or resp.additional_kwargs.get("token_counts")

                if usage:
                    # Handle Pydantic or Dict
                    i_tok = 0
                    o_tok = 0
                    if isinstance(usage, dict):
                        i_tok = usage.get("prompt_tokens") or usage.get("input_tokens", 0)
                        o_tok = usage.get("completion_tokens") or usage.get("output_tokens", 0)
                    else:
                        i_tok = getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0)
                        o_tok = getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0)

                    return {"input": i_tok, "output": o_tok}

        except Exception as e:
            logger.warning(f"Error extracting usage from payload: {e}")

        return None
