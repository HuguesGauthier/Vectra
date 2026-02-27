"""
Ambiguity Guard Agent
=====================
Schema-driven agent that collects required filters from the user
before authorizing a search against Qdrant.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from jinja2 import Template

from llama_index.core.llms import LLM
from .ambiguity_prompt import AMBIGUITY_GUARD_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Constants
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_LENGTH = 500


class AmbiguityAction(str, Enum):
    PROCEED = "SEARCH_PROCEED"
    CLARIFY = "CLARIFY"
    # Legacy — kept for backward compat but no longer generated
    SUGGEST = "SUGGEST_FACETS"


class AmbiguityDecision(BaseModel):
    action: AmbiguityAction
    extracted_filters: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


class AmbiguityGuardAgent:
    """
    Schema-driven agent that collects required filters one by one.

    Decision logic:
    - If all filter_exact_cols are present → SEARCH_PROCEED
    - If any are missing → CLARIFY (ask for the next missing one)
    
    Filters are accumulated across conversation turns by the caller.
    """

    def __init__(self, llm: LLM):
        self.llm = llm
        self.template = Template(AMBIGUITY_GUARD_PROMPT_TEMPLATE)

    async def analyze_query(
        self,
        query: str,
        ai_schema: Dict[str, Any],
        chat_history: Optional[List[Any]] = None,
        facets: Optional[Dict[str, List[str]]] = None,
        accumulated_filters: Optional[Dict[str, Any]] = None,
    ) -> AmbiguityDecision:
        """
        Main entry point. Determines what filters are still needed.

        Args:
            query: Current user message.
            ai_schema: The CSV's ai_schema (contains filter_exact_cols, filter_range_cols).
            chat_history: Full conversation history.
            facets: Available values per filter column (from Qdrant).
            accumulated_filters: Filters already collected in previous turns.
        """
        try:
            exact_cols = ai_schema.get("filter_exact_cols", [])
            range_cols = ai_schema.get("filter_range_cols", [])

            if not exact_cols and not range_cols:
                logger.info("ℹ️ Guard bypassed: No filters defined in schema.")
                return self._proceed(accumulated_filters or {})

            acc = dict(accumulated_filters or {})

            # Build prompt with full context
            prompt = self._build_prompt(query, ai_schema, acc, facets, chat_history)

            logger.info("🔍 AmbiguityGuard: Analyzing query...")
            response_text = await self._execute_llm_safe(prompt)

            # Parse LLM response
            decision = self._parse_llm_result(response_text)

            # Normalize keys and values using schema + facets
            self._normalize_filters_and_keys(decision.extracted_filters, exact_cols + range_cols, facets)

            # Override action: deterministically check if all required filters are present
            all_filters = {**acc, **decision.extracted_filters}
            missing = self._get_missing_exact_filters(exact_cols, all_filters)

            if missing:
                decision.action = AmbiguityAction.CLARIFY
                # Ensure message is set (LLM should have set it, but be safe)
                if not decision.message:
                    next_missing = missing[0]
                    facet_hint = ""
                    if facets and next_missing in facets:
                        facet_hint = f" (ex: {', '.join(facets[next_missing][:5])})"
                    decision.message = f"Could you specify the **{next_missing}**?{facet_hint}"
            else:
                decision.action = AmbiguityAction.PROCEED

            # Always return full accumulated filters
            decision.extracted_filters = all_filters

            return decision

        except Exception as e:
            logger.error(f"❌ Ambiguity analysis failed: {e}", exc_info=True)
            # Fail open: let the retrieval happen with whatever we have
            return self._proceed(accumulated_filters or {})

    # --- Private: Core Logic ---

    def _get_missing_exact_filters(self, exact_cols: List[str], filters: Dict[str, Any]) -> List[str]:
        """Returns list of required exact filter columns that haven't been provided yet."""
        filters_lower = {k.lower() for k in filters.keys()}
        return [col for col in exact_cols if col.lower() not in filters_lower]

    def _normalize_filters_and_keys(
        self,
        extracted: Dict[str, Any],
        all_schema_cols: List[str],
        facets: Optional[Dict[str, List[str]]],
    ) -> None:
        """
        Normalizes:
        1. Keys: maps lowercase keys to canonical schema column names.
        2. Values: maps user values to canonical facet values (case-insensitive).
        """
        canonical_keys = {col.lower(): col for col in all_schema_cols}

        normalized = {}
        for key, val in extracted.items():
            canonical_key = canonical_keys.get(key.lower(), key)

            # Value normalization
            if facets and canonical_key in facets and val:
                val_lower = str(val).strip().lower()
                for facet_val in facets[canonical_key]:
                    if str(facet_val).strip().lower() == val_lower:
                        val = facet_val
                        break

            normalized[canonical_key] = val

        extracted.clear()
        extracted.update(normalized)

    def _build_prompt(
        self,
        query: str,
        schema: Dict[str, Any],
        accumulated_filters: Dict[str, Any],
        facets: Optional[Dict],
        history: Optional[List[Any]],
    ) -> str:
        """Renders the Jinja2 prompt with all context."""
        exact_cols = schema.get("filter_exact_cols", [])
        range_cols = schema.get("filter_range_cols", [])
        missing_exact = self._get_missing_exact_filters(exact_cols, accumulated_filters)
        history_text = self._format_chat_history(history)

        return self.template.render(
            query=query,
            exact_filters=exact_cols,
            range_filters=range_cols,
            accumulated_filters=accumulated_filters,
            missing_exact=missing_exact,
            facets=facets or {},
            conversation_history=history_text,
        )

    def _format_chat_history(self, history: Optional[List[Any]]) -> str:
        """Formats recent user and assistant messages for context."""
        if not history:
            return ""

        recent = history[-MAX_HISTORY_MESSAGES:]
        lines = []
        for msg in recent:
            role = getattr(msg, "role", None) or msg.get("role")
            content = getattr(msg, "content", None) or msg.get("content")
            if role in ("user", "assistant") and content:
                prefix = "User" if role == "user" else "Assistant"
                lines.append(f"{prefix}: {str(content)[:MAX_MESSAGE_LENGTH]}")

        return "\n".join(lines)

    def _sanitize_json_text(self, text: str) -> str:
        """Strips markdown code fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        return text.strip()

    def _parse_llm_result(self, text: str) -> AmbiguityDecision:
        """Parses LLM JSON response into AmbiguityDecision."""
        clean = self._sanitize_json_text(text)
        try:
            data = json.loads(clean)
            action_val = data.get("action", "CLARIFY")
            try:
                data["action"] = AmbiguityAction(action_val)
            except ValueError:
                data["action"] = AmbiguityAction.CLARIFY

            # The prompt uses "filters" not "extracted_filters"
            if "filters" in data and "extracted_filters" not in data:
                data["extracted_filters"] = data.pop("filters")

            return AmbiguityDecision(**{k: v for k, v in data.items() if k in AmbiguityDecision.model_fields})
        except Exception as e:
            logger.warning(f"⚠️ Ambiguity parse failed: {e}. Raw: {text[:150]}")
            return AmbiguityDecision(action=AmbiguityAction.CLARIFY, extracted_filters={})

    async def _execute_llm_safe(self, prompt: str) -> str:
        """Calls LLM safely."""
        response = await self.llm.acomplete(prompt)
        return response.text.strip()

    def _proceed(self, filters: Dict[str, Any]) -> AmbiguityDecision:
        """Helper: create a PROCEED decision."""
        return AmbiguityDecision(action=AmbiguityAction.PROCEED, extracted_filters=filters)
