import asyncio
import logging
import time
from typing import Any, Dict, Optional

from llama_index.core.callbacks.base import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType

from app.services.chat.types import PipelineStepType

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Callback Handler that pushes LlamaIndex events to an asyncio Queue
    for streaming to the UI.
    """

    def __init__(self, queue: asyncio.Queue, language: str = "en"):
        # Initialize parent with empty ignore lists to capture all specific events we observe
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.queue = queue
        self.language = language
        self._event_map = {}  # Track context (step_type, label) by event_id
        self._event_starts = {}
        self._has_used_tools = False
        self._is_sql_flow = False
        # Token metrics
        self.total_input_tokens = 0
        self.total_output_tokens = 0

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

        # Phase 1: Identification (Start Phase)
        if phase == "start":
            step_type = self._determine_step_type(event_type, payload)
            if step_type:
                self._event_map[event_id] = {"step_type": step_type, "label": label}

        # Phase 2: Processing & Recovery (End Phase)
        else:
            stored = self._event_map.pop(event_id, None)
            if stored:
                step_type = stored["step_type"]
                label = stored.get("label")
            else:
                return

        if not step_type:
            return

        # Metrics
        duration = None
        token_count = None

        if phase == "end":
            start_time = self._event_starts.pop(event_id, None)
            if start_time:
                duration = round(time.time() - start_time, 3)

            if payload:
                token_count = self._extract_usage_from_payload(payload)

        # Build final payload
        out_payload = {}
        if duration is not None:
            out_payload["duration"] = duration

        if token_count:
            out_payload["tokens"] = token_count
            self.total_input_tokens += token_count.get("input", 0)
            self.total_output_tokens += token_count.get("output", 0)

        # Specific payload enrichments
        if step_type == PipelineStepType.RETRIEVAL:
            self._enrich_retrieval_payload(payload, out_payload)

        # Dispatch
        event_data = {
            "step_type": step_type,
            "status": "running" if phase == "start" else "completed",
            "payload": out_payload,
            "duration": duration,
            "label": label,
        }

        try:
            self.queue.put_nowait(event_data)
        except asyncio.QueueFull:
            logger.warning("Streaming queue is full, dropping event.")

    def _determine_step_type(self, event_type: CBEventType, payload: Optional[Dict]) -> Optional[PipelineStepType]:
        """Encapsulates heuristic logic to identify pipeline steps from raw LlamaIndex events."""

        # Tool Execution
        if event_type == CBEventType.FUNCTION_CALL:
            self._has_used_tools = True
            return PipelineStepType.TOOL_EXECUTION

        # Retrieval
        if event_type == CBEventType.RETRIEVE:
            return PipelineStepType.RETRIEVAL

        # Agent Step (General Processing)
        if event_type == CBEventType.AGENT_STEP:
            return PipelineStepType.ROUTER_PROCESSING

        # LLM Calls (Reasoning, Synthesis, SQL, Selection)
        if event_type == CBEventType.LLM:
            # If tools were used previously, this LLM call is likely the final synthesis
            if self._has_used_tools:
                return PipelineStepType.ROUTER_SYNTHESIS

            # Otherwise, analyze payload to distinguish between SQL, Router, or Reasoning
            return self._analyze_llm_payload(payload)

        return None

    def _analyze_llm_payload(self, payload: Optional[Dict]) -> PipelineStepType:
        """Deep inspection of LLM payload to guess the intent (SQL vs Select vs Reasoning)."""
        is_sql = False
        is_select = False

        if not payload:
            return PipelineStepType.ROUTER_REASONING

        # Strategy A: Check Messages content
        if "messages" in payload:
            for msg in payload["messages"]:
                content = str(msg.content).lower()
                if "sql" in content and "table" in content:
                    is_sql = True
                if "postgresql" in content:
                    is_sql = True
                if "select statement" in content:
                    is_sql = True

                # Selection keywords override SQL hints often found in router prompts
                if "choices:" in content or ("select" in content and "tool" in content):
                    is_sql = False
                    is_select = True

                if is_sql or is_select:
                    break

        # Strategy B: Check Serialized Class Names (Strong Signal)
        if not is_sql and not is_select and "serialized" in payload:
            serialized = str(payload["serialized"])
            if "NLSQLRetriever" in serialized or "SQL" in serialized:
                is_sql = True
            elif "Selector" in serialized:
                is_select = True

        # Strategy C: Check Template Vars (LlamaIndex specific)
        if not is_sql and not is_select and "template_vars" in payload:
            t_vars = payload["template_vars"]
            if isinstance(t_vars, dict):
                if "choices" in t_vars and len(t_vars.get("choices", [])) > 1:
                    is_select = True
                elif "schema" in t_vars or "dialect" in t_vars:
                    is_sql = True

        # Conclusion
        if is_sql:
            self._is_sql_flow = True
            return PipelineStepType.SQL_GENERATION
        if is_select:
            return PipelineStepType.ROUTER_SELECTION

        return PipelineStepType.ROUTER_REASONING

    def _enrich_retrieval_payload(self, payload: Optional[Dict], out_payload: Dict):
        """Extracts source counts and flow hints for Retrieval steps."""
        if not payload:
            out_payload["source_count"] = 0
            return

        nodes = payload.get("nodes", [])
        out_payload["source_count"] = len(nodes)

        # SQL Flow Detection
        if self._is_sql_flow:
            out_payload["is_sql"] = True
            return

        serialized = str(payload.get("serialized", ""))
        if (
            "NLSQLRetriever" in serialized
            or "SQLRetriever" in serialized
            or ("SQL" in serialized and "Table" in serialized)
        ):
            out_payload["is_sql"] = True
            self._is_sql_flow = True

    def _extract_usage_from_payload(self, payload: Dict) -> Optional[Dict]:
        """Safely extracts token usage from Gemini or OpenAI style payloads."""
        try:
            # 1. Direct 'usage' key
            if "usage" in payload and isinstance(payload["usage"], dict):
                return {
                    "input": payload["usage"].get("prompt_tokens", 0),
                    "output": payload["usage"].get("completion_tokens", 0),
                }

            # 2. Inspect 'response' object
            resp = payload.get("response")
            if not resp:
                return None

            raw = getattr(resp, "raw", None)

            # Gemini (usage_metadata)
            if raw:
                # raw might be dict or object
                meta = raw.get("usage_metadata") if isinstance(raw, dict) else getattr(raw, "usage_metadata", None)

                if meta:
                    # meta might be dict or object
                    if isinstance(meta, dict):
                        return {
                            "input": meta.get("prompt_token_count", 0),
                            "output": meta.get("candidates_token_count", 0),
                        }
                    else:
                        return {
                            "input": getattr(meta, "prompt_token_count", 0),
                            "output": getattr(meta, "candidates_token_count", 0),
                        }

            # OpenAI / Generic
            usage = None
            if isinstance(raw, dict):
                usage = raw.get("usage")

            if not usage and hasattr(resp, "additional_kwargs"):
                usage = resp.additional_kwargs.get("usage") or resp.additional_kwargs.get("token_counts")

            if usage:
                # Normalized extraction
                i = usage.get("prompt_tokens") or usage.get("input_tokens") or getattr(usage, "prompt_tokens", 0)
                o = (
                    usage.get("completion_tokens")
                    or usage.get("output_tokens")
                    or getattr(usage, "completion_tokens", 0)
                )
                return {"input": int(i or 0), "output": int(o or 0)}

        except Exception as e:
            logger.warning(f"Error extracting usage from payload: {e}")

        return None

    # Required Abstract Methods
    def start_trace(self, trace_id: Optional[str] = None) -> None:
        pass

    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict[str, Any]] = None) -> None:
        pass
