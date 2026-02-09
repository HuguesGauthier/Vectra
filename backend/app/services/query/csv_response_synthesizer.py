"""
CSV Response Synthesizer
========================
Formulates structured technical sheets from retrieved CSV data using LLM.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from jinja2 import Template
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore

# Config / Prompts
from app.services.query.response_synthesis_prompt import (
    DYNAMIC_TECH_SHEET_SYSTEM_PROMPT, SIMPLE_TECH_SHEET_PROMPT)

logger = logging.getLogger(__name__)

# Constants
SCHEMA_FILTER_COLS = "filter_exact_cols"
SCHEMA_SEMANTIC_COLS = "semantic_cols"
SCHEMA_RENAMING = "renaming_map"
SCHEMA_START_YEAR = "start_year_col"

TIMEOUT_SYNTHESIS_SEC = 45.0  # Increased from 15.0 to handle complex/verbose generations


class CsvResponseSynthesizer:
    """
    Synthesizes structured technical sheet responses for CSV queries.

    Responsibilities (SRP):
    1. Context Assembly (Nodes -> String).
    2. Prompt Engineering (Template Rendering).
    3. LLM Orchestration (Generation with Timeout).
    4. Response Parsing (Clean JSON extraction).
    """

    def __init__(self, llm: LLM):
        self.llm = llm
        self.template = Template(DYNAMIC_TECH_SHEET_SYSTEM_PROMPT)
        # self.simple_template = Template(SIMPLE_TECH_SHEET_PROMPT) # Reserved for future use

    async def synthesize_response(
        self,
        query: str,
        retrieved_nodes: List[NodeWithScore],
        ai_schema: Dict[str, Any],
        use_simple_format: bool = False,
        instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the generation of the technical sheet.
        """
        try:
            # 1. Prepare Data Context
            reverse_map = self._build_reverse_mapping(ai_schema)
            context_str = self._build_context_from_nodes(retrieved_nodes, reverse_map)

            # 2. Build Prompt
            full_prompt = self._construct_prompt(
                query=query,
                ai_schema=ai_schema,
                reverse_map=reverse_map,
                context=context_str,
                instructions=instructions,
            )

            # 3. Execute LLM (With Timeout)
            logger.info("📝 Synthesizing Tech Sheet...")
            response_text = await self._execute_llm(full_prompt)

            # 4. Parse & Return
            return self._parse_json_response(response_text)

        except Exception as e:
            logger.error(f"❌ Synthesis failed: {e}", exc_info=True)
            return self._create_error_response(str(e))

    # --- Private Methods: Logic Atomization ---

    def _build_reverse_mapping(self, start_schema: Dict[str, Any]) -> Dict[str, str]:
        """Creates a map from internal column name to human-readable label."""
        renaming = start_schema.get(SCHEMA_RENAMING, {})
        return {v: k for k, v in renaming.items()}

    def _construct_prompt(
        self,
        query: str,
        ai_schema: Dict[str, Any],
        reverse_map: Dict[str, str],
        context: str,
        instructions: Optional[str],
    ) -> str:
        """Renders the Jinja2 template."""
        system_prompt = self.template.render(
            user_query=query,
            filter_exact_cols=ai_schema.get(SCHEMA_FILTER_COLS, []),
            semantic_cols=ai_schema.get(SCHEMA_SEMANTIC_COLS, []),
            original_names=reverse_map,
            has_years_covered=ai_schema.get(SCHEMA_START_YEAR) is not None,
            assistant_instructions=instructions,
        )
        return f"{system_prompt}\n\n**CONTEXT:**\n{context}"

    async def _execute_llm(self, prompt: str) -> str:
        """Executes LLM with Timeout Protection."""
        try:
            response = await asyncio.wait_for(self.llm.acomplete(prompt), timeout=TIMEOUT_SYNTHESIS_SEC)
            return response.text
        except asyncio.TimeoutError:
            logger.error(f"Synthesis timed out after {TIMEOUT_SYNTHESIS_SEC}s")
            raise Exception("Response generation timed out.")

    def _build_context_from_nodes(self, nodes: List[NodeWithScore], reverse_map: Dict[str, str]) -> str:
        """
        Formats retrieved nodes into a readable string for the LLM.
        REMOVED: Local file IO (debug dumping) for security/performance.
        """
        if not nodes:
            return "No relevant products found."

        context_parts = []

        # Limit context to top 5 to avoid token overflow
        for i, node_with_score in enumerate(nodes[:5], 1):
            node = node_with_score.node
            meta = node.metadata or {}

            # Header
            context_parts.append(f"**Product {i}** (Confidence: {node_with_score.score:.2f})")
            context_parts.append(f"Description: {node.text}")

            # Metadata Construction
            if meta:
                context_parts.append("### Specifications:")
                for key, val in meta.items():
                    # Formatting logic moved here to keep loop clean
                    val_str = self._format_metadata_value(key, val)
                    label = reverse_map.get(key, key)

                    # Logic: Skip raw year cols if years_covered array exists (cleaner context)
                    if key in ["year_start", "year_end"] and "years_covered" in meta:
                        continue

                    context_parts.append(f"- {label}: {val_str}")

            context_parts.append("")  # Spacer

        return "\n".join(context_parts)

    def _format_metadata_value(self, key: str, value: Any) -> str:
        """Helper to format complex metadata values (lists, years)."""
        if key == "years_covered" and isinstance(value, list) and value:
            if len(value) > 1:
                return f"{min(value)}-{max(value)}"
            return str(value[0])
        return str(value)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Cleans and extracts JSON from LLM response."""
        clean_text = text.strip()

        # Strip Markdown Fences
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`")
            if clean_text.startswith("json"):
                clean_text = clean_text[4:]
            clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.warning(f"JSON Parse Error. Raw text: {clean_text[:100]}...")
            # Fallback: Return text as description
            return {"title": "Information", "description": clean_text, "specifications": []}

    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Returns a standardized error structure."""
        return {
            "title": "Generation Error",
            "description": f"Unable to generate technical specifications: {error_msg}",
            "specifications": [],
        }


def should_use_csv_synthesizer(connector_type: str, ai_schema: Optional[Dict[str, Any]]) -> bool:
    """Helper predicate to determine if this synthesizer applies."""
    return connector_type == "local_file" and ai_schema is not None and bool(ai_schema.get(SCHEMA_FILTER_COLS))
