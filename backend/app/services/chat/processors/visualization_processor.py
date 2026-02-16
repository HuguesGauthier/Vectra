import json
import logging
import time
from typing import AsyncGenerator, Dict, Any

from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.types import ChatContext, PipelineStepType
from app.services.chat.utils import EventFormatter
from app.services.visualization_service import VisualizationService

# Force use of the main 'app' logger
logger = logging.getLogger("app")


class VisualizationProcessor(BaseChatProcessor):
    """
    Intelligent visualization orchestrator.

    Responsibility (SRP):
    - Determines if visualization is needed (Orchestration Predicate).
    - Delegates Data Extraction, Classification, and Formatting to VisualizationService.
    - Yields events and metrics to the pipeline.
    """

    def __init__(self):
        super().__init__()
        # Service Composition (Stateless Service)
        self.viz_service = VisualizationService()

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Main entry point for visualization processing.
        """
        logger.info("VisualizationProcessor.process() CALLED")

        try:
            # 1. Eligibility Check (Fast Guard Clause)
            if not self._should_run_visualization(ctx):
                logger.info("Visualization skipped based on eligibility checks.")
                return

            # 2. Start Pipeline Step
            yield EventFormatter.format(PipelineStepType.VISUALIZATION_ANALYSIS, "running", ctx.language)
            start_time = time.time()

            # 3. AI Decision - Should we visualize? (Synchronous check now)
            should_visualize = self._ask_ai_for_visualization(ctx)

            if not should_visualize:
                logger.info("AI decided no visualization needed")
                duration = round(time.time() - start_time, 3)
                self._record_metrics(ctx, duration, {})
                yield EventFormatter.format(
                    PipelineStepType.VISUALIZATION_ANALYSIS,
                    "completed",
                    ctx.language,
                    payload={"status": "skipped_no_request"},
                    duration=duration,
                )
                return

            # 4. Execution Phase (Delegated to Service)

            # A. Extract Data
            data_info = await self.viz_service.extract_data_info(ctx)

            if data_info.row_count == 0:
                logger.warning("No data extracted - aborting visualization")
                duration = round(time.time() - start_time, 3)
                self._record_metrics(ctx, duration, {})
                yield EventFormatter.format(
                    PipelineStepType.VISUALIZATION_ANALYSIS,
                    "completed",
                    ctx.language,
                    payload={"status": "skipped_no_data"},
                    duration=duration,
                )
                return

            # B. Classify Type
            viz_type, tokens = await self.viz_service.classify_visualization_type(ctx, data_info)
            logger.info(f"Classified as: {viz_type}")

            # C. Format Data
            viz_data = self.viz_service.format_visualization_data(ctx, viz_type, data_info)
            ctx.visualization = viz_data

            # 5. Completion & Metrics
            duration = round(time.time() - start_time, 3)
            self._record_metrics(ctx, duration, tokens)

            yield EventFormatter.format(
                PipelineStepType.VISUALIZATION_ANALYSIS,
                "completed",
                ctx.language,
                payload={"tokens": tokens},
                duration=duration,
            )

            # 6. Output Generation (Dedup Check)
            if self._is_redundant_table(viz_type, ctx):
                return

            if viz_data:
                logger.info("Sending visualization payload")
                yield json.dumps({"type": "visualization", "data": viz_data}, default=str) + "\n"

        except Exception as e:
            logger.error(f"Visualization process failed: {e}", exc_info=True)
            yield EventFormatter.format(
                PipelineStepType.VISUALIZATION_ANALYSIS, "failed", ctx.language, payload={"error": str(e)}
            )

    # --- Orchestration Predicates ---

    def _should_run_visualization(self, ctx: ChatContext) -> bool:
        """Quick eligibility check before asking AI for visualization decision."""
        # 1. Check existing visualization
        if ctx.visualization and getattr(ctx.visualization, "viz_type", "none") != "none":
            return False

        # 2. Check empty response (Unless we have SQL results/Shortcut)
        if not ctx.full_response_text and not ctx.sql_results:
            return False

        # 3. Check for blocking patterns (Negative Signals)
        # Using context manager or safer access if full_response_text could be None?
        # Type hint says str, but let's be safe.
        response_text = ctx.full_response_text or ""
        blocking_patterns = ["je n'ai trouvé aucun", "no products found", "pas de résultat"]
        response_lower = response_text.lower()

        if any(p in response_lower for p in blocking_patterns):
            return False

        # 4. Check if we have potential data (SQL or Vector)
        if ctx.sql_results or ctx.retrieved_sources:
            return True

        return False

    def _record_metrics(self, ctx: ChatContext, duration: float, tokens: Dict[str, int]):
        """Records telemetry."""
        if ctx.metrics:
            ctx.metrics.record_completed_step(
                step_type=PipelineStepType.VISUALIZATION_ANALYSIS,
                label="Visualization Analysis",
                duration=duration,
                input_tokens=tokens.get("input", 0),
                output_tokens=tokens.get("output", 0),
            )

    def _ask_ai_for_visualization(self, ctx: ChatContext) -> bool:
        """
        Determines if visualization should be generated based on user intent.
        Now synchronous as it currently only does keyword matching.
        """
        message_lower = (ctx.message or "").lower()

        # Explicit visualization keywords
        viz_keywords = {
            "graph",
            "chart",
            "visualize",
            "visualise",
            "treemap",
            "pie",
            "bar",
            "line",
            "courbe",
            "camembert",
            "histogramme",
            "graphique",
            "area",
            "aire",
            "surface",
            "stacked",
            "empilé",
            "empile",
            "funnel",
            "entonnoir",
            "pyramide",
            "scatter",
            "nuage",
            "dispersion",
            "points",
            "radar",
            "araignée",
            "polar",
            "polaire",
            "radial",
            "jauge",
            "gauge",
            "heatmap",
            "chaleur",
            "slope",
            "pente",
        }

        # Check for explicit request (Set lookup is O(1))
        # Simple loop is fine given logical OR nature
        if any(kw in message_lower for kw in viz_keywords):
            logger.info(f"Explicit visualization request detected.")
            return True

        logger.info(f"No explicit visualization request found.")
        return False

    def _is_redundant_table(self, viz_type: str, ctx: ChatContext) -> bool:
        """
        Prevents showing a Table card if the response already contains a GenUI table block.
        """
        if viz_type != "table":
            return False

        # Safe access to metadata
        if not ctx.metadata:
            return False

        content_blocks = ctx.metadata.get("content_blocks", [])
        return any(block.get("type") == "table" for block in content_blocks)
