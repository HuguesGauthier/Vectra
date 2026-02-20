import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StepMetric:
    step_type: str
    label: str
    start_time: float
    step_id: str = ""  # Unique ID for nesting
    parent_id: Optional[str] = None  # Reference to parent span
    end_time: float = 0.0
    duration: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    sequence: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    sub_steps: List["StepMetric"] = field(default_factory=list)

    @property
    def is_completed(self) -> bool:
        return self.end_time > 0.0


class ChatMetricsManager:
    """
    Centralized manager for tracking all steps in a chat request.
    Single source of truth for time and tokens.
    """

    def __init__(self):
        self.start_time: float = time.time()
        self.steps: Dict[str, StepMetric] = {}  # Keyed by step_type or unique ID
        self.completed_steps: List[StepMetric] = []
        self._step_counter: int = 0
        self._sequence_counter: int = 0

        # Aggregates
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.ttft: float = 0.0  # Time to First Token
        self.custom_metrics: Dict[str, Any] = {}  # For legacy/custom usage (e.g. cache_hit)

    def __setitem__(self, key: str, value: Any):
        """Allow dict-style setting for legacy code compatibility."""
        if key == "ttft":
            self.ttft = float(value)
        elif key == "input_tokens":
            self.total_input_tokens = int(value)
        elif key == "output_tokens":
            self.total_output_tokens = int(value)
        else:
            self.custom_metrics[key] = value

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style getting with lazy evaluation."""
        if key == "ttft":
            return self.ttft
        if key == "input_tokens":
            return self.total_input_tokens
        if key == "output_tokens":
            return self.total_output_tokens
        if key == "total_duration":
            return round(time.time() - self.start_time, 3)

        # Retrieve summary only if complex keys are requested
        # or if key is not found in fast paths (could be in custom_metrics)
        # Note: get_summary() builds the whole dict, which is heavy.
        # We try to look in custom_metrics first as a common fallback?
        # The original code did: summary = self.get_summary(); return summary[key]
        # get_summary() merges custom_metrics into the result.
        # So if key is in custom_metrics, it returns it.

        if key in self.custom_metrics:
            return self.custom_metrics[key]

        # Fallback for calculated fields usually found in summary
        summary = self.get_summary()
        return summary[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Safe get method."""
        try:
            return self[key]
        except KeyError:
            return default

    def start_span(self, step_type: str, label: Optional[str] = None, parent_id: Optional[str] = None) -> str:
        """Start a new timing span. Returns a unique span ID."""
        if not label:
            label = step_type.replace("_", " ").title()

        span_id = f"{step_type}_{self._step_counter}"
        self._step_counter += 1

        self.steps[span_id] = StepMetric(
            step_type=step_type, 
            label=label, 
            start_time=time.time(),
            step_id=span_id,
            parent_id=parent_id
        )
        # Assign sequence at START to preserve nesting order (Parent < Children)
        self.steps[span_id].sequence = self._sequence_counter
        self._sequence_counter += 1
        return span_id

    def end_span(
        self,
        span_id: str,
        payload: Optional[Dict] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        increment_total: bool = True,
    ):
        """End a timing span and record metrics."""
        if span_id not in self.steps:
            return  # Should log warning

        step = self.steps.pop(span_id)
        step.end_time = time.time()
        step.duration = round(step.end_time - step.start_time, 3)

        # Extract tokens from payload if not provided explicitly
        if payload and "tokens" in payload:
            t = payload["tokens"]
            input_tokens = t.get("input_tokens", 0)
            output_tokens = t.get("output_tokens", 0)

        step.input_tokens = input_tokens
        step.output_tokens = output_tokens
        if payload:
            step.metadata = payload

        if increment_total:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

        # Sequence is already assigned at start_span
        self.completed_steps.append(step)
        return step

    def record_completed_step(
        self,
        step_type: str,
        label: str,
        duration: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        payload: Dict = None,
        increment_total: bool = True,
        parent_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ):
        """Manually record a step that was tracked elsewhere (e.g. internally in a callback)."""
        # Create a synthetic step
        now = time.time()
        sid = step_id or f"{step_type}_sync_{self._step_counter}"
        self._step_counter += 1

        step = StepMetric(
            step_type=step_type,
            label=label,
            start_time=now - duration,
            end_time=now,
            duration=duration,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata=payload or {},
            step_id=sid,
            parent_id=parent_id,
        )

        if increment_total:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

        step.sequence = self._sequence_counter
        self._sequence_counter += 1
        self.completed_steps.append(step)
        return sid

    def get_summary(self) -> Dict:
        """Return compatible dictionary for existing frontend/API contracts."""
        # Sort steps by sequence to preserve absolute chronological order
        sorted_steps = sorted(self.completed_steps, key=lambda x: x.sequence)

        summary = {
            "total_duration": round(time.time() - self.start_time, 3),
            "ttft": self.ttft,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "step_breakdown": [
                {
                    "step_id": s.step_id,
                    "parent_id": s.parent_id,
                    "step_type": s.step_type,
                    "label": s.label,
                    "duration": s.duration,
                    "sequence": s.sequence,
                    "tokens": {"input": s.input_tokens, "output": s.output_tokens},
                    "metadata": s.metadata,
                    **({"sub_steps": [
                        {
                            "step_id": ss.step_id,
                            "parent_id": ss.parent_id,
                            "step_type": ss.step_type,
                            "label": ss.label,
                            "duration": ss.duration,
                            "sequence": ss.sequence,
                            "tokens": {"input": ss.input_tokens, "output": ss.output_tokens},
                            "metadata": ss.metadata,
                        }
                        for ss in s.sub_steps
                    ]} if s.sub_steps else {}),
                }
                for s in sorted_steps
            ],
            # Merged dict for legacy analytics/DB persistence
            "legacy_step_breakdown": self._get_merged_durations(),
            "legacy_step_token_breakdown": self._get_merged_tokens(),
        }
        # Merge custom metrics
        summary.update(self.custom_metrics)
        return summary

    def _get_merged_durations(self) -> Dict[str, float]:
        res = {}
        for s in self.completed_steps:
            res[s.step_type] = round(res.get(s.step_type, 0.0) + s.duration, 3)
        return res

    def _get_merged_tokens(self) -> Dict[str, Dict[str, int]]:
        res = {}
        for s in self.completed_steps:
            if s.input_tokens > 0 or s.output_tokens > 0:
                t = res.get(s.step_type, {"input_tokens": 0, "output_tokens": 0})
                t["input_tokens"] += s.input_tokens
                t["output_tokens"] += s.output_tokens
                res[s.step_type] = t
        return res
