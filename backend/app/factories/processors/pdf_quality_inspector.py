"""
PDF Quality Inspector - Analyzes extracted text quality to determine processing strategy.

PURPOSE:
- Detect empty/scanned PDFs (OCR required)
- Detect encoding corruption (garbled text)
- Calculate quality score to decide local vs cloud routing

USAGE:
    inspector = PdfQualityInspector()
    score = inspector.calculate_quality_score(text)
    if score < 40:
        # Use cloud processor (LlamaParse)
    else:
        # Keep local result (pypdf)
"""

from __future__ import annotations

import logging
import re
from typing import Final

logger = logging.getLogger(__name__)


class PdfQualityInspector:
    """
    Analyzes PDF text extraction quality to optimize processing costs.

    STRATEGY:
    - High quality (score >= 40) → Keep local/free result
    - Low quality (score < 40) → Use cloud/paid processor
    """

    # Quality thresholds (configurable)
    MIN_CHARS_FOR_VALID: Final[int] = 50
    MAX_GIBBERISH_RATIO: Final[float] = 0.6  # Max ratio of non-alphanumeric chars
    MIN_QUALITY_SCORE: Final[int] = 40  # Threshold for local acceptance

    # Known corruption patterns
    UNICODE_REPLACEMENT_CHARS: Final[set] = {"�", "\ufffd", "\ufeff"}

    @staticmethod
    def is_empty(text: str) -> bool:
        """
        Detect if text is empty or whitespace-only.

        INDICATES: PDF is scanned (images only), no extractable text.

        Returns:
            True if empty/whitespace, False otherwise
        """
        return not text or not text.strip()

    @staticmethod
    def is_too_short(text: str, min_chars: int = MIN_CHARS_FOR_VALID) -> bool:
        """
        Detect if text is too short to be useful content.

        INDICATES: Page contains only page numbers, logos, or minimal metadata.

        Args:
            text: Text to analyze
            min_chars: Minimum character threshold (default: 50)

        Returns:
            True if text length below threshold
        """
        return len(text.strip()) < min_chars

    @classmethod
    def has_encoding_issues(cls, text: str) -> bool:
        """
        Detect encoding corruption or garbled text.

        INDICATORS:
        - Unicode replacement characters (�)
        - Excessive non-alphanumeric ratio (gibberish)
        - Repetitive invalid sequences

        Returns:
            True if encoding problems detected
        """
        if not text:
            return False

        # Check for Unicode replacement chars
        has_replacement_chars = any(char in text for char in cls.UNICODE_REPLACEMENT_CHARS)
        if has_replacement_chars:
            return True

        # Calculate ratio of non-alphanumeric characters
        total_chars = len(text)
        if total_chars == 0:
            return False

        # Count alphanumeric + common punctuation as "valid"
        valid_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in ".,;:!?-()[]{}\"'/\\")
        gibberish_ratio = 1 - (valid_chars / total_chars)

        return gibberish_ratio > cls.MAX_GIBBERISH_RATIO

    @classmethod
    def is_sparse_form(cls, text: str) -> bool:
        """
        Detect if text looks like a sparse form template (labels without values).
        Common in scanned forms where pypdf only sees the printed mask.
        """
        if not text:
            return False

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return False

        # Count "suspicious" lines ending in separators without value
        suspicious_lines = 0
        for line in lines:
            # Matches "Label:" or "Label : $" or "Label__________"
            if line.endswith(":") or line.endswith("$") or "_" * 5 in line:
                suspicious_lines += 1
            # Matches short label+separator only (e.g. "Date:")
            elif len(line) < 20 and ":" in line:
                suspicious_lines += 1

        # If > 30% of lines are suspicious, it's likely an un-filled or un-scanned form
        ratio = suspicious_lines / len(lines)
        return ratio > 0.3

    @classmethod
    def is_table_detected(cls, text: str) -> bool:
        """
        Detect table-like structures (e.g. pipe separators).
        pypdf handles tables poorly, so we should prefer Cloud/OCR.
        """
        if not text:
            return False

        # Check for pipe table markers
        pipe_count = text.count("|")
        line_count = text.count("\n")

        # Heuristic: If meaningful number of pipes relative to content
        if pipe_count > 5:
            logger.debug(f"table_detection: found {pipe_count} pipes")
            return True

        return False

    @classmethod
    def calculate_quality_score(cls, text: str) -> int:
        """
        Calculate text quality score (0-100).

        SCORING ALGORITHM:
        - 100: Perfect extraction (clean, substantial text)
        - 60-80: Good quality (minor issues)
        - 40-60: Acceptable (usable but degraded)
        - 0-40: Poor (requires cloud processing)

        Args:
            text: Extracted text to analyze

        Returns:
            Quality score (0-100)
        """
        if not text:
            return 0

        score = 100  # Start perfect

        # Penalty 1: Empty or whitespace-only (-100)
        if cls.is_empty(text):
            logger.debug("quality_penalty: empty_text | -100")
            return 0

        # Penalty 2: Too short (-50)
        if cls.is_too_short(text):
            penalty = 50
            score -= penalty
            logger.debug(f"quality_penalty: too_short | -{penalty} | chars={len(text.strip())}")

        # Penalty 3: Encoding issues (-40)
        if cls.has_encoding_issues(text):
            penalty = 40
            score -= penalty
            logger.debug(f"quality_penalty: encoding_issues | -{penalty}")

        # Penalty 4: Sparse Form Detection (-60) [Force Cloud]
        # Detects templates with labels but missing values (e.g. "Name: ____")
        # Heuristic: High ratio of lines ending in colons or special chars without content
        if cls.is_sparse_form(text):
            penalty = 70
            score -= penalty
            logger.debug(f"quality_penalty: sparse_form_detected | -{penalty}")

        # Penalty 5: Table Detection (-60 to -80 for forced fallback)
        # pypdf destroys tables. Force cloud if we see table markers.
        if cls.is_table_detected(text):
            penalty = 80
            score -= penalty
            logger.debug(f"quality_penalty: table_detected | -{penalty}")

        # Bonus: Long content (+10)
        if len(text.strip()) > 1000:
            bonus = 10
            score = min(100, score + bonus)
            logger.debug(f"quality_bonus: substantial_content | +{bonus}")

        # Bonus: Multiple paragraphs (+5)
        paragraph_count = text.count("\n\n")
        if paragraph_count >= 3:
            bonus = 5
            score = min(100, score + bonus)
            logger.debug(f"quality_bonus: multi_paragraph | +{bonus}")

        return max(0, min(100, score))  # Clamp to [0, 100]

    @classmethod
    def should_use_cloud(cls, text: str, threshold: int | None = None) -> bool:
        """
        Final decision: should we use cloud processor?

        LOGIC:
        - Empty text → YES (likely scanned PDF, needs OCR)
        - Quality score < threshold → YES (poor extraction)
        - Quality score >= threshold → NO (local result acceptable)

        Args:
            text: Extracted text
            threshold: Custom quality threshold (default: MIN_QUALITY_SCORE)

        Returns:
            True if cloud processing recommended, False if local OK
        """
        threshold = threshold or cls.MIN_QUALITY_SCORE
        quality_score = cls.calculate_quality_score(text)

        use_cloud = quality_score < threshold

        logger.info(
            "pdf_quality_decision",
            extra={
                "quality_score": quality_score,
                "threshold": threshold,
                "use_cloud": use_cloud,
                "reason": cls._get_decision_reason(text, quality_score),
            },
        )

        return use_cloud

    @classmethod
    def _get_decision_reason(cls, text: str, score: int) -> str:
        """
        Get human-readable reason for routing decision.

        Returns:
            Reason string for logging
        """
        if cls.is_empty(text):
            return "text_empty_likely_scanned"
        if cls.is_too_short(text):
            return "text_too_short"
        if cls.has_encoding_issues(text):
            return "encoding_corrupted"
        if cls.is_sparse_form(text):
            return "sparse_form_template"
        if score >= cls.MIN_QUALITY_SCORE:
            return "local_quality_sufficient"
        return "quality_below_threshold"
