import json
from typing import Any, Optional


class EventFormatter:
    """Helper to format SSE events with centralized localization via PipelineRegistry."""

    @staticmethod
    def format(
        step_type: Any,
        status: Any,
        language: str,
        payload: Optional[Any] = None,
        duration: Optional[float] = None,
        label: Optional[str] = None,
    ) -> str:
        # P0 FIX: Ensure Enums are converted to strings/values for JSON
        step_val = step_type.value if hasattr(step_type, "value") else str(step_type)
        status_val = status.value if hasattr(status, "value") else str(status)

        # USER_REQUEST: Frontend handles I18n. Backend sends keys only.
        # We generally do NOT resolve labels here anymore.
        # But we respect explicit dynamic labels from callers (e.g. "Processing file X")
        final_label = label

        # If explicitly passed distinct "label" override, use it (dynamic info).
        # Otherwise send None so frontend uses generic I18n key.

        data = {"type": "step", "step_type": step_val, "status": status_val, "label": final_label}
        if payload is not None:
            data["payload"] = payload
        if duration is not None:
            data["duration"] = duration

        return json.dumps(data, default=str) + "\n"
