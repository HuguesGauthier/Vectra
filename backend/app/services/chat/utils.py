import json
from typing import Any, Optional


class EventFormatter:
    """Helper to format SSE events with centralized localization via PipelineRegistry."""

    @staticmethod
    def format(
        step_type: Any,
        status: Any,
        step_id: str,
        parent_id: Optional[str] = None,
        payload: Optional[Any] = None,
        duration: Optional[float] = None,
        label: Optional[str] = None,
    ) -> str:
        # P0 FIX: Ensure Enums are converted to strings/values for JSON
        step_val = step_type.value if hasattr(step_type, "value") else str(step_type)
        status_val = status.value if hasattr(status, "value") else str(status)

        # Backend sends Step ID and Parent ID for robust nesting. 
        # Labels are handled by the Frontend (i18n) unless a dynamic override is provided.
        data = {
            "type": "step", 
            "step_type": step_val, 
            "status": status_val, 
            "step_id": step_id,
            "parent_id": parent_id
        }
        
        if label:
            data["label"] = label
            
        if payload is not None:
            data["payload"] = payload

        if duration is not None:
            data["duration"] = duration

        return json.dumps(data, default=str) + "\n"


async def resolve_embedding_provider(ctx: Any) -> str:
    """
    Resolves the embedding provider with fallback logic.
    Priority: Context Cache > Connector > Global Settings > Default ("ollama")

    Args:
        ctx: ChatContext (typed as Any to avoid circular imports if necessary, but try importing first)
    """
    # 1. From Context Cache
    if getattr(ctx, "embedding_provider", None):
        return ctx.embedding_provider

    # 2. From Connectors
    if hasattr(ctx.assistant, "linked_connectors") and ctx.assistant.linked_connectors:
        for conn in ctx.assistant.linked_connectors:
            # Access configuration safely
            config = getattr(conn, "configuration", {}) or {}
            # Handle both object and dict access if needed (ORM quirk safe)
            if not isinstance(config, dict):
                config = {}

            provider = config.get("ai_provider") or config.get("embedding_provider")
            if provider:
                ctx.embedding_provider = provider
                return provider

    # 3. Global Settings
    provider = await ctx.settings_service.get_value("embedding_provider")
    if provider:
        ctx.embedding_provider = provider
        return provider

    # 4. Default
    ctx.embedding_provider = "ollama"
    return "ollama"
