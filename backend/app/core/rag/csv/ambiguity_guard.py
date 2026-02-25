"""
Ambiguity Guard Agent - Core Implementation
============================================
Pre-search agent that analyzes CSV queries for missing mandatory filters.
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from jinja2 import Template
# Core Imports
from llama_index.core.llms import LLM
from pydantic import BaseModel, Field

# Config
from app.core.rag.csv.ambiguity_prompt import AMBIGUITY_GUARD_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# Constants (No Magic Numbers)
TIMEOUT_LLM_ANALYSIS: float = 8.0  # Seconds - Strict budget for ambiguity check
MAX_HISTORY_MESSAGES: int = 6
MAX_MESSAGE_LENGTH: int = 200

# --- Enums & Models ---


class AmbiguityAction(str, Enum):
    """
    Possible actions decided by the agent.
    Inherits from str for easy JSON serialization.
    """

    PROCEED = "PROCEED"  # Query is clear, search immediately
    SUGGEST = "SUGGEST_FACETS"  # Query is vague, suggest specific options
    CLARIFY = "CLARIFY"  # Query is nonsensical or needs user input


class AmbiguityAnalysis(BaseModel):
    """
    Structured output expected from the LLM.
    Strictly typed for validation.
    """

    action: Union[str, AmbiguityAction] = Field(
        ..., description="Decision code (SEARCH_PROCEED, SUGGEST_FACETS, CLARIFY)"
    )
    filters: Dict[str, str] = Field(default_factory=dict, description="Extracted key-value pairs for filtering.")
    message: Optional[str] = Field(None, description="Clarification message or suggestion context.")


class AmbiguityDecision(BaseModel):
    """
    Internal decision object passed to the Processor.
    """

    action: AmbiguityAction
    extracted_filters: Dict[str, str] = Field(default_factory=dict)
    message: Optional[str] = None

    @property
    def should_search(self) -> bool:
        return self.action == AmbiguityAction.PROCEED


# --- Main Service ---


class AmbiguityGuardAgent:
    """
    Pre-search agent for detecting ambiguous CSV queries.

    Responsibilities (SRP):
    1. Context Preparation (Schema & History Normalization).
    2. LLM Execution (Prompting & Parsing).
    3. Decision Mapping (Raw LLM output -> Domain Decision).

    Security & Resilience (Audit P0/P1):
    - Circuit Breaker: Enforced timeouts on LLM calls.
    - Defensive Parsing: Handles malformed JSON gracefully.
    - Safe Defaults: Fails open (PROCEED) on error to avoid blocking user flow.
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
    ) -> AmbiguityDecision:
        """
        Main entry point for query analysis.
        """
        try:
            # 1. Validation & Preprocessing (Guard Clause)
            filter_cols = self._extract_filter_columns(ai_schema)
            if not filter_cols:
                logger.info("ℹ️ Guard bypassed: No mandatory filters defined in schema.")
                return self._create_safe_decision()

            # 2. Context Construction
            prompt = self._build_prompt(query, ai_schema, filter_cols, chat_history, facets)

            # 3. Execution (With Circuit Breaker)
            logger.info("🔍 AmbiguityGuard: Analyzing Query...")
            response_text = await self._execute_llm_safe(prompt)

            # 4. Parsing & Mapping
            return self._parse_llm_result(response_text)

        except Exception as e:
            # P2: Structured Error Logging
            logger.error(f"❌ Ambiguity analysis critical failure: {e}", exc_info=True)
            return self._create_safe_decision()

    # --- Private Methods: Logic Atomization ---

    def _extract_filter_columns(self, schema: Dict[str, Any]) -> List[str]:
        """Merges exact and range filters from schema."""
        exact = schema.get("filter_exact_cols", [])
        ranges = schema.get("filter_range_cols", [])
        return exact + ranges

    def _build_prompt(
        self,
        query: str,
        schema: Dict[str, Any],
        params: List[str],
        history: Optional[List[Any]],
        facets: Optional[Dict],
    ) -> str:
        """Constructs the analysis prompt with history context."""

        # Format History
        history_text = self._format_chat_history(history)

        # Build Reverse Map safely
        renaming = schema.get("renaming_map", {})
        reverse_map = {v: k for k, v in renaming.items()}

        return self.template.render(
            query=query,
            exact_filters=schema.get("filter_exact_cols", []),
            range_filters=schema.get("filter_range_cols", []),
            all_filters=params,
            original_names=reverse_map,
            conversation_history=history_text,
            facets=facets or {},
        )

    async def _execute_llm_safe(self, prompt: str) -> str:
        """
        Executes LLM call with Circuit Breaker (Timeout Protection).
        """
        try:
            # P0: Async Timeout Protection
            response = await asyncio.wait_for(self.llm.acomplete(prompt), timeout=TIMEOUT_LLM_ANALYSIS)
            return response.text

        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Ambiguity Guard Timed Out after {TIMEOUT_LLM_ANALYSIS}s - Defaulting to PROCEED")
            return "{}"  # Return empty JSON to trigger safe default parsing

        except Exception as e:
            logger.warning(f"⚠️ LLM Execution Failed: {e}")
            return "{}"

    def _parse_llm_result(self, text: str) -> AmbiguityDecision:
        """Parses JSON output and maps to internal Decision model."""
        clean_text = self._sanitize_json_text(text)

        if not clean_text or clean_text == "{}":
            return self._create_safe_decision()

        try:
            data = json.loads(clean_text)
            analysis = AmbiguityAnalysis(**data)

            # Map raw string action to Enum
            action_map = {
                "SEARCH_PROCEED": AmbiguityAction.PROCEED,
                "SUGGEST_FACETS": AmbiguityAction.SUGGEST,
                "CLARIFY": AmbiguityAction.CLARIFY,
                "PROCEED": AmbiguityAction.PROCEED,  # Fallback
            }

            # Default to PROCEED if unknown action
            raw_action = str(analysis.action).upper()
            final_action = action_map.get(raw_action, AmbiguityAction.PROCEED)

            logger.info(f"✅ Decision: {final_action.value} | Filters: {len(analysis.filters)}")

            return AmbiguityDecision(action=final_action, extracted_filters=analysis.filters, message=analysis.message)

        except (json.JSONDecodeError, ValueError) as e:
            # P2: Improve error logging with head of invalid text
            preview = clean_text[:100].replace("\n", " ")
            logger.warning(f"⚠️ Failed to parse Ambiguity JSON: {e}. Text: '{preview}...' -> Defaulting to PROCEED.")
            return self._create_safe_decision()

    def _format_chat_history(self, history: Optional[List[Any]]) -> str:
        """Extracts and formats recent user messages."""
        if not history:
            return ""

        # Take last N messages (Token Efficiency)
        recent = history[-MAX_HISTORY_MESSAGES:]
        user_msgs = []

        for msg in recent:
            # Handle both dicts and Objects (LlamaIndex types)
            role = getattr(msg, "role", None) or msg.get("role")
            content = getattr(msg, "content", None) or msg.get("content")

            if role == "user" and content:
                # Truncate for token efficiency
                user_msgs.append(f"- {str(content)[:MAX_MESSAGE_LENGTH]}")

        if not user_msgs:
            return ""

        return "Previous user messages:\n" + "\n".join(user_msgs)

    def _sanitize_json_text(self, text: str) -> str:
        """Removes markdown fences if present."""
        text = text.strip()
        if text.startswith("```"):
            # Remove first line (```json) and last line (```)
            lines = text.split("\n")
            if len(lines) >= 2:
                # Defensive check: sometimes it's just ``` without json
                # Also handle cases where ``` is inline? Less likely for full response
                return "\n".join(lines[1:-1]).strip()
        return text

    def _create_safe_decision(self) -> AmbiguityDecision:
        """Returns a fail-safe 'Proceed' decision."""
        # Fail Open Strategy: Assume we should search rather than block the user if agent fails
        return AmbiguityDecision(action=AmbiguityAction.PROCEED, extracted_filters={})
