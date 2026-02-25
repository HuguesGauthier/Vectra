import logging
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.ingestion import IndexingStrategy

logger = logging.getLogger(__name__)


class SmartRowTransformer:
    """
    The Muscle: Transforms raw CSV rows into Rich Vector Candidates.

    LOSSLESS PAYLOAD APPROACH:
    - ALL CSV columns are preserved in the payload
    - Smart transformations are applied on top (type enforcement, enrichments)
    - Semantic text is built from classified columns only
    """

    def __init__(self, strategy: IndexingStrategy):
        self.strategy = strategy

    def transform(self, record: Dict[str, Any], line_number: int) -> Tuple[str, Dict[str, Any]]:
        """
        Input: Raw row dict + Line Number
        Output: (Semantic Text, Rich Payload)

        CRITICAL: Payload contains ALL columns from the CSV row + enrichments.
        """
        # ========================================================================
        # STEP 1: BASE PAYLOAD - ALL COLUMNS (LOSSLESS FOUNDATION)
        # ========================================================================
        payload = dict(record)  # Start with EVERY column from the CSV

        # ========================================================================
        # STEP 2: TYPE ENFORCEMENT FOR FILTER COLUMNS
        # ========================================================================
        # Ensure filter columns have proper types (e.g., "2010" -> 2010)
        # We combine both lists and use a set to avoid processing the same column twice
        filter_cols = set(self.strategy.filter_exact_cols) | set(self.strategy.filter_range_cols)
        for col in filter_cols:
            if col in payload and payload[col] is not None:
                payload[col] = self._enforce_type(payload[col])

        # ========================================================================
        # STEP 3: ENRICHMENT - YEARS COVERED (ADDITIVE, NOT DESTRUCTIVE)
        # ========================================================================
        if self.strategy.start_year_col and self.strategy.end_year_col:
            try:
                start_val = payload.get(self.strategy.start_year_col)
                end_val = payload.get(self.strategy.end_year_col)

                if start_val is not None and end_val is not None:
                    # Robust parsing (handle strings/floats)
                    s_year = int(float(start_val))
                    e_year = int(float(end_val))

                    # Sanity check and order verification
                    if 1900 < s_year < 2100 and 1900 < e_year < 2100 and s_year <= e_year:
                        # Generate years list [2010, 2011, 2012, ...]
                        years = list(range(s_year, e_year + 1))

                        # ADD computed fields (don't remove originals)
                        payload["years_covered"] = years
                        payload["year_start"] = s_year
                        payload["year_end"] = e_year
            except (ValueError, TypeError):
                # Graceful degradation - skip enrichment but keep row
                logger.debug(f"Could not parse years for row {line_number}")
                pass

        # ========================================================================
        # STEP 4: SEMANTIC TEXT CONSTRUCTION
        # ========================================================================
        # Build embedding text from SEMANTIC columns only
        # These columns stay in payload (dual purpose: searchable + displayable)
        text_parts = []
        for col in self.strategy.semantic_cols:
            val = record.get(col)
            if val is not None and str(val).strip():
                # Narrative format: "Description: brake pads..."
                text_parts.append(f"{col}: {val}")

        semantic_text = "\n".join(text_parts)

        # Fallback if no semantic columns defined or all empty
        if not semantic_text:
            semantic_text = "\n".join([f"{k}: {v}" for k, v in record.items() if v is not None and str(v).strip()])

        # ========================================================================
        # STEP 5: METADATA (Internal tracking fields)
        # ========================================================================
        payload["_line_number"] = line_number
        if self.strategy.primary_id_col:
            payload["primary_id"] = record.get(self.strategy.primary_id_col)

        return semantic_text, payload

    def _enforce_type(self, value: Any) -> Any:
        """
        Type enforcement helper: Cast to int/float if possible, otherwise keep as string.

        Examples:
            "2010" -> 2010 (int)
            "19.99" -> 19.99 (float)
            "Category A" -> "Category A" (str)
            None -> None
        """
        if value is None or value == "":
            return None

        # Already correct type
        if isinstance(value, (int, float)):
            return value

        # String parsing
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            try:
                # Try int first (no decimal point)
                if "." not in value:
                    return int(value)
                # Try float
                return float(value)
            except (ValueError, TypeError):
                # Keep as string if numeric parsing fails
                return value

        # Other types (lists, dicts) - return as-is
        return value
