"""
PDF Processor - Smart hybrid processor with quality-based routing.

STRATEGY (LOCAL-FIRST FOR COST/SPEED OPTIMIZATION):
1. Try PdfLocalProcessor (pypdf) first - FREE, fast, local
2. Analyze quality with PdfQualityInspector:
   - Empty text (scanned PDF) → Use cloud (Gemini) with OCR/Multimodal
   - Corrupted encoding → Use cloud
   - Quality score < 40 → Use cloud
   - Quality score >= 40 → Keep local result (SAVE LATENCY)
3. Cloud fallback (Gemini) only if:
   - Local quality insufficient
   - API key available

COST OPTIMIZATION: 80%+ of PDFs with native text stay local.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.exceptions import ConfigurationError
from app.core.settings import get_settings
from app.factories.processors.base import FileProcessor, ProcessedDocument
from app.factories.processors.pdf_cloud_processor import GeminiProcessorError, PdfCloudProcessor
from app.factories.processors.pdf_local_processor import PdfLocalProcessor
from app.factories.processors.pdf_quality_inspector import PdfQualityInspector

logger = logging.getLogger(__name__)


class PdfProcessor(FileProcessor):
    """
    Hybrid PDF processor with intelligent quality-based routing.

    ARCHITECTURE: Strategy Pattern with Quality Inspection
    - Attempts LOCAL processing (pypdf) first - FREE and FAST
    - Analyzes extraction quality with PdfQualityInspector
    - Routes to cloud (Gemini) ONLY if quality insufficient or OCR needed
    - Transparent to callers - always returns ProcessedDocument

    BENEFITS:
    - Reduced latency (most PDFs stay local)
    - Automatic OCR/Multimodal detection for scanned PDFs
    - Intelligent quality-based routing
    - Graceful degradation if API key missing
    """

    def __init__(self):
        """Initialize both processors."""
        super().__init__(max_file_size_bytes=100 * 1024 * 1024)

        # Initialize both processors
        self._cloud_processor = PdfCloudProcessor()
        self._local_processor = PdfLocalProcessor()

        logger.info("pdf_processor_initialized", extra={"mode": "hybrid_local_first"})

    @property
    def _has_api_key(self) -> bool:
        """Helper for internal routing and backward compatibility with tests."""
        return get_settings().GEMINI_API_KEY is not None

    async def process(self, file_path: str | Path) -> list[ProcessedDocument]:
        """
        Process PDF with smart local-first routing.

        STRATEGY:
        1. Try local processor first (pypdf) - FREE
        2. Analyze quality with PdfQualityInspector
        3. If quality good → keep local result (save latency)
        4. If quality poor → use cloud (Gemini)

        Returns:
            List with single ProcessedDocument (always succeeds or returns error doc)
        """
        # Quick validation
        try:
            validated_path = await self._validate_file_path(file_path)
        except Exception as e:
            return [ProcessedDocument(content="", metadata={"file_type": "pdf"}, success=False, error_message=str(e))]

        # ========== STRATEGY 1: TRY LOCAL FIRST (FREE) ==========
        logger.info("pdf_attempting_local_processing_first", extra={"processor": "pypdf", "cost": "$0"})

        try:
            local_result = await self._local_processor.process(str(validated_path))

            # Check if local processing succeeded
            if local_result and local_result[0].success:
                content = local_result[0].content

                # ========== 100% TEXT CHECK ==========
                # User Requirement: "If not 100% text (i.e., has images), use Cloud"
                has_images = any(doc.metadata.get("has_images", False) for doc in local_result)

                if has_images:
                    logger.warning(
                        "pdf_images_detected_forcing_cloud",
                        extra={"processor": "pypdf", "reason": "not_100_percent_text", "next_step": "cloud_fallback"},
                    )
                    # Force fallback by skipping to Cloud block
                    # We do this by NOT returning here
                else:
                    # ========== QUALITY INSPECTION ==========
                    quality_score = PdfQualityInspector.calculate_quality_score(content)
                    should_use_cloud = PdfQualityInspector.should_use_cloud(content)

                    # Decision point
                    if not should_use_cloud:
                        # ✅ LOCAL QUALITY SUFFICIENT - KEEP RESULT
                        logger.info(
                            "pdf_local_processing_sufficient",
                            extra={"processor": "pypdf", "quality_score": quality_score, "decision": "local_accepted"},
                        )
                        return local_result

                    # ❌ QUALITY INSUFFICIENT - NEED CLOUD
                    logger.warning(
                        "pdf_local_quality_insufficient_trying_cloud",
                        extra={
                            "quality_score": quality_score,
                            "reason": PdfQualityInspector._get_decision_reason(content, quality_score),
                            "next_step": "cloud_fallback",
                        },
                    )
            else:
                # Local processing returned error
                logger.warning(
                    "pdf_local_processing_failed_trying_cloud",
                    extra={
                        "error": local_result[0].error_message if local_result else "unknown",
                        "next_step": "cloud_fallback",
                    },
                )

        except Exception as e:
            # Unexpected local processing error
            logger.error("pdf_local_processor_unexpected_error_trying_cloud", extra={"error": str(e)}, exc_info=True)

        # ========== STRATEGY 2: CLOUD FALLBACK (GEMINI) ==========
        if not self._has_api_key:
            logger.warning(
                "pdf_no_cloud_key_keeping_local_result",
                extra={"quality": "potentially_poor", "suggestion": "configure_GEMINI_API_KEY"},
            )
            return local_result or [
                ProcessedDocument(
                    content="",
                    metadata={"file_type": "pdf"},
                    success=False,
                    error_message="All PDF processors failed and no cloud API key available",
                )
            ]

        logger.info("pdf_attempting_cloud_processing", extra={"processor": "Gemini", "has_ocr": True})

        try:
            cloud_result = await self._cloud_processor.process(str(validated_path))

            # Check if cloud processing succeeded
            if cloud_result and cloud_result[0].success:
                logger.info(
                    "pdf_cloud_processing_successful", extra={"processor": "Gemini", "decision": "cloud_accepted"}
                )
                return cloud_result

            # Cloud processing returned error document
            logger.error(
                "pdf_cloud_processing_failed",
                extra={"reason": cloud_result[0].error_message if cloud_result else "unknown"},
            )

            # Return cloud error (more informative than generic error)
            return cloud_result

        except (ConfigurationError, GeminiProcessorError) as e:
            # Expected errors - log and return error doc
            logger.error("pdf_cloud_processor_error", extra={"error": str(e), "processor": "Gemini"})

            return [
                ProcessedDocument(
                    content="",
                    metadata={"file_type": "pdf"},
                    success=False,
                    error_message=f"Cloud processing failed: {str(e)}",
                )
            ]

        except Exception as e:
            # Unexpected error - log with full stack
            logger.error(
                "pdf_cloud_processor_unexpected_error",
                extra={"error": str(e), "processor": "Gemini"},
                exc_info=True,
            )

            return [
                ProcessedDocument(
                    content="",
                    metadata={"file_type": "pdf"},
                    success=False,
                    error_message=f"Unexpected cloud error: {str(e)}",
                )
            ]

        # ========== NO CLOUD KEY AVAILABLE ==========
        # Keep local result even if quality is poor (no alternative)
        logger.warning(
            "pdf_no_cloud_key_keeping_local_result",
            extra={"quality": "potentially_poor", "suggestion": "configure_GEMINI_API_KEY"},
        )

        # Return local result if available, otherwise generic error
        if local_result:
            return local_result

        return [
            ProcessedDocument(
                content="",
                metadata={"file_type": "pdf"},
                success=False,
                error_message="All PDF processors failed and no cloud API key available",
            )
        ]

    def get_supported_extensions(self) -> list[str]:
        """Supported extensions."""
        return ["pdf"]
