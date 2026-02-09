import asyncio
import json
import logging
import time
from typing import (Any, AsyncGenerator, Dict, List, NamedTuple, Optional,
                    Tuple, cast)
from uuid import UUID

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.repositories import DocumentRepository
from app.services.chat.processors.base_chat_processor import (
    BaseChatProcessor, ChatProcessorError)
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter, LLMFactory
# CSV Components
from app.services.query.ambiguity_guard import (AmbiguityDecision,
                                                AmbiguityGuardAgent)
from app.services.query.csv_response_synthesizer import CsvResponseSynthesizer
from app.services.query.csv_retrieval_service import CSVRetrievalService
from app.services.query.facet_query_service import FacetQueryService

logger = logging.getLogger(__name__)

# --- Constants ---
STEP_CONNECTION = PipelineStepType.CONNECTION
STEP_RETRIEVAL = PipelineStepType.CSV_SCHEMA_RETRIEVAL
ACTION_CLARIFY = "CLARIFY"
ACTION_SUGGEST = "SUGGEST_FACETS"
TIMEOUT_RETRIEVAL = 30.0
TIMEOUT_SYNTHESIS = 60.0
TIMEOUT_CSV_STEP = 45.0
KEY_ERROR = "error"


# --- Types ---
class CSVComponents(NamedTuple):
    """Immutable configuration for CSV Pipeline components."""

    llm: Any
    embed_model: Any
    qdrant_client: Any
    collection_name: str
    vector_index: VectorStoreIndex
    # Service Facade
    retrieval_service: CSVRetrievalService


class CSVRAGProcessor(BaseChatProcessor):
    """
    Processor specialized for CSV RAG operations.

    Enforces distinct phases:
    1. Validation & Initialization
    2. Ambiguity Analysis & Query Rewriting
    3. Schema-Aware Retrieval (Delegated to CSVRetrievalService)
    4. Tech Sheet Synthesis
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Executes the CSV RAG pipeline with strict phase isolation and service delegation.
        """
        try:
            # 0. Pre-flight Check
            should_run, ai_schema = await self.should_use_csv_pipeline(ctx)
            if not should_run or not ai_schema:
                return

            logger.info(f"🔥 Starting CSV RAG Pipeline for Session: {ctx.session_id}")

            # 1. Initialization
            yield EventFormatter.format(STEP_CONNECTION, "running", ctx.language, payload={"is_substep": True})
            t0 = time.time()
            try:
                # Pure Async Call (No Yields)
                components = await asyncio.wait_for(self._prepare_csv_components(ctx), timeout=45.0)
                dur = round(time.time() - t0, 3)
                yield EventFormatter.format(
                    STEP_CONNECTION, "completed", ctx.language, duration=dur, payload={"is_substep": True}
                )
            except asyncio.TimeoutError:
                yield EventFormatter.format(
                    STEP_CONNECTION,
                    StepStatus.FAILED,
                    ctx.language,
                    label="CSV Setup Timeout",
                    payload={"is_substep": True},
                )
                return
            except Exception as e:
                logger.error(f"Setup failed: {e}")
                yield EventFormatter.format(
                    STEP_CONNECTION, StepStatus.FAILED, ctx.language, label="Setup Error", payload={"is_substep": True}
                )
                return

            if not components:
                yield self._format_error("Failed to initialize components")
                return

            # 2. Ambiguity & Rewrite Phase
            async for event in self._run_ambiguity_phase(ctx, components, ai_schema):
                yield event

            # Retrieve decision from Side-Effect
            decision = ctx.metadata.get("ambiguity_decision", {})
            action = decision.get("action")

            if action == ACTION_CLARIFY:
                yield self._yield_token_message(ctx, decision.get("message", "Could you clarify?"))
                self._mark_executed(ctx)
                return

            elif action == ACTION_SUGGEST:
                suggestion_nodes = await components.retrieval_service.suggest(
                    query=ctx.message, extracted_filters=decision.get("extracted_filters", {})
                )

                if suggestion_nodes:
                    ctx.metadata["csv_retrieved_nodes"] = suggestion_nodes
                else:
                    self._mark_executed(ctx)
                    return

            # 3. Retrieval Phase
            if "csv_retrieved_nodes" not in ctx.metadata:
                # Find the correct connector (CSV)
                connector = next((c for c in ctx.assistant.linked_connectors if c.connector_type == "csv"), None)
                if not connector and ctx.assistant.linked_connectors:
                    connector = ctx.assistant.linked_connectors[0]  # Fallback

                if not connector:
                    yield self._format_error("No connector found for CSV retrieval")
                    return

                connector_id = connector.id
                async for event in self._consume_with_timeout(
                    self._process_csv_retrieval(ctx, components, decision, connector_id), TIMEOUT_RETRIEVAL
                ):
                    yield event

            # 4. Synthesis Phase
            async for event in self._consume_with_timeout(
                self._process_csv_synthesis(ctx, components.llm, ai_schema), TIMEOUT_SYNTHESIS
            ):
                yield event

            self._mark_executed(ctx)

        except asyncio.TimeoutError:
            logger.error("CSV Pipeline Stage Timeout")
            yield json.dumps({"type": KEY_ERROR, "message": "Processing timed out."}, default=str) + "\n"
        except Exception as e:
            logger.error(f"CSV Pipeline Critical Failure: {e}", exc_info=True)
            yield json.dumps({"type": KEY_ERROR, "message": f"Error: {str(e)[:50]}"}, default=str) + "\n"

    def _mark_executed(self, ctx: ChatContext) -> None:
        """Marks the pipeline as executed to prevent fallback RAG."""
        ctx.metadata["csv_pipeline_executed"] = True

    # --- Phase 2: Ambiguity & Logic ---

    async def _run_ambiguity_phase(
        self, ctx: ChatContext, components: CSVComponents, ai_schema: Dict
    ) -> AsyncGenerator[str, None]:
        """Runs the ambiguity guard and rewrite logic."""
        async for event in self._consume_with_timeout(
            self._process_csv_ambiguity_guard(ctx, components.llm, ai_schema), TIMEOUT_CSV_STEP
        ):
            yield event

    async def _process_csv_ambiguity_guard(
        self, ctx: ChatContext, llm: Any, ai_schema: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        t0 = time.time()
        yield EventFormatter.format(
            PipelineStepType.AMBIGUITY_GUARD, "running", ctx.language, payload={"is_substep": True}
        )

        try:
            # Find the CSV connector to get connector_id
            connector = next((c for c in ctx.assistant.linked_connectors if c.connector_type == "csv"), None)
            if not connector and ctx.assistant.linked_connectors:
                connector = ctx.assistant.linked_connectors[0]  # Fallback

            if not connector:
                logger.error("No connector found for CSV ambiguity guard")
                yield EventFormatter.format(
                    PipelineStepType.AMBIGUITY_GUARD,
                    "failed",
                    ctx.language,
                    label="No Connector",
                    payload={"is_substep": True},
                )
                return

            connector_id = connector.id

            # Logic: Fetch Facets
            # P0 FIX: Use the connector's ai_provider for collection name
            # Extract ai_provider from connector configuration, fallback to global setting
            if connector.configuration.get("ai_provider"):
                embedding_provider = connector.configuration.get("ai_provider")
            else:
                embedding_provider = await ctx.settings_service.get_value("embedding_provider", default="local")

            collection_name = await ctx.vector_service.get_collection_name(embedding_provider)
            qdrant_client = ctx.vector_service.get_qdrant_client()
            facet_service = FacetQueryService(qdrant_client)

            facets = {}
            for col in ai_schema.get("filter_exact_cols", []):
                values = await facet_service.get_facet_values(
                    collection_name=collection_name, facet_field=col, connector_id=connector_id, limit=50
                )
                if values:
                    facets[col] = values

            # Logic: Rewriting
            rewritten_query = await self._execute_rewrite(ctx, llm)
            if rewritten_query:
                ctx.message = rewritten_query
                logger.info(f"🔄 Rewritten Query: {rewritten_query}")

            # Logic: Agent Analysis
            agent = AmbiguityGuardAgent(llm=llm)
            decision = await agent.analyze_query(ctx.message, ai_schema, ctx.history, facets)

            # Side Effect: Store Decision
            ctx.metadata["ambiguity_decision"] = {
                "action": decision.action,
                "extracted_filters": decision.extracted_filters,
                "message": decision.message,
            }

            dur = round(time.time() - t0, 3)
            yield EventFormatter.format(
                PipelineStepType.AMBIGUITY_GUARD,
                "completed",
                ctx.language,
                payload={"decision": decision.action, "is_substep": True},
                duration=dur,
            )

        except Exception as e:
            logger.error(f"Ambiguity guard failed: {e}")
            ctx.metadata["ambiguity_decision"] = {"action": "PROCEED", "extracted_filters": {}, "message": None}
            yield EventFormatter.format(
                PipelineStepType.AMBIGUITY_GUARD,
                "completed",
                ctx.language,
                duration=round(time.time() - t0, 3),
                payload={"is_substep": True},
            )

    async def _execute_rewrite(self, ctx: ChatContext, llm: Any) -> Optional[str]:
        """Executes query rewriting to merge conversational context."""
        from app.core.rag.processors.rewriter import QueryRewriterProcessor
        from app.core.rag.types import PipelineContext

        temp_ctx = PipelineContext(
            user_message=ctx.message,
            chat_history=ctx.history,
            language=ctx.language,
            assistant=ctx.assistant,
            llm=llm,
            embed_model=None,
            search_strategy=None,
        )

        rewriter = QueryRewriterProcessor()
        async for _ in rewriter.process(temp_ctx):
            pass  # Consume
        return temp_ctx.rewritten_query

    # --- Phase 3: Retrieval ---

    async def _process_csv_retrieval(
        self, ctx: ChatContext, components: CSVComponents, decision: Dict, connector_id: UUID
    ) -> AsyncGenerator[str, None]:
        t0 = time.time()
        yield EventFormatter.format(STEP_RETRIEVAL, "running", ctx.language, payload={"is_substep": True})

        try:
            filters = decision.get("extracted_filters", {})

            # P1: Generate and capture embedding for Trending analysis
            # The retriever will generate it anyway, but we need to capture it explicitly
            try:
                embedding = await components.embed_model.aget_query_embedding(ctx.message)
                ctx.question_embedding = embedding
            except Exception as e:
                logger.warning(f"Failed to capture question embedding for trending: {e}")

            # Strict Service Delegation
            nodes = await components.retrieval_service.search(
                query=ctx.message, filters=filters, connector_id=connector_id, top_k=ctx.assistant.top_k_retrieval or 10
            )

            ctx.metadata["csv_retrieved_nodes"] = nodes

            dur = round(time.time() - t0, 3)
            yield EventFormatter.format(
                STEP_RETRIEVAL,
                "completed",
                ctx.language,
                payload={"count": len(nodes), "is_substep": True},
                duration=dur,
            )

        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            yield EventFormatter.format(STEP_RETRIEVAL, "failed", ctx.language, payload={"is_substep": True})

    # --- Phase 4: Synthesis ---

    async def _process_csv_synthesis(self, ctx: ChatContext, llm: Any, ai_schema: Dict) -> AsyncGenerator[str, None]:
        t0 = time.time()
        yield EventFormatter.format(
            PipelineStepType.CSV_SYNTHESIS, "running", ctx.language, payload={"is_substep": True}
        )

        try:
            nodes = ctx.metadata.get("csv_retrieved_nodes", [])
            synthesizer = CsvResponseSynthesizer(llm=llm)

            data = await synthesizer.synthesize_response(
                query=ctx.message,
                retrieved_nodes=nodes,
                ai_schema=ai_schema,
                use_simple_format=False,
                instructions=ctx.assistant.instructions if ctx.assistant else None,
            )

            # Derive human-readable text for history/storage (avoid raw JSON in DB)
            summary = (
                data.get("summary")
                or data.get("description")
                or data.get("message")
                or "Information extracted from CSV."
            )
            ctx.full_response_text = str(summary)

            dur = round(time.time() - t0, 3)
            yield EventFormatter.format(
                PipelineStepType.CSV_SYNTHESIS, "completed", ctx.language, duration=dur, payload={"is_substep": True}
            )

            # Stream Outputs using the standard protocol
            async for event in self._stream_synthesis_content(ctx, data):
                yield event

        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            yield EventFormatter.format(
                PipelineStepType.CSV_SYNTHESIS, "failed", ctx.language, payload={"is_substep": True}
            )

    async def _stream_synthesis_content(self, ctx: ChatContext, data: Dict) -> AsyncGenerator[str, None]:
        """Formats the synthesis result into standard streamable tokens."""
        # Robust text extraction: check Multiple Keys
        # The LLM might use 'summary', 'description', or 'message'
        summary = data.get("summary") or data.get("description") or data.get("message")

        # Fallback: if it's a list or dict without those keys, stringify it
        if not summary and data:
            # If there's no explicit summary but we have data, we don't want to be silent
            if isinstance(data, dict) and "products" in data and not data.get("products"):
                summary = "Aucun produit correspondant n'a été trouvé."

        if summary:
            logger.info(f"✅ [CSV_STREAM] Yielding summary token (length: {len(str(summary))})")
            # Standard Token Protocol for main chat bubble
            # We ensure it's a string
            yield self._format_token(str(summary))
        else:
            logger.warning("⚠️ [CSV_STREAM] No text summary found in synthesis data!")

        # P1: Save tech sheets to ctx.visualization for persistence
        products = data.get("products", [])
        if products:
            ctx.visualization = {"type": "tech-sheet", "items": products}
            logger.info(f"💾 Saved {len(products)} tech sheets to ctx.visualization for persistence")

        # Tech sheets are complex objects, we still use the tech-sheet block type
        # but wrapped in a recognizable event if needed, or just yield as is if handled by frontend.
        # Actually, tech-sheets are usually rendered by a specific component.
        # Let's ensure the summary (text) is definitely visible.
        for product in products:
            # For now, let's yield the tech-sheet as a special block if the frontend expects it.
            # Based on previous code, it was json.dumps(...) + \n.
            # I'll keep the tech-sheet but ensure it's not swallowed.
            yield json.dumps(
                {"type": "content_block", "block_type": "tech-sheet", "content": product}, default=str
            ) + "\n"

    # --- Helpers & Utilities ---

    async def should_use_csv_pipeline(self, ctx: ChatContext) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Detects if the request targets a CSV connector with valid schema."""
        try:
            if not ctx.assistant.linked_connectors:
                return False, None

            first_connector = ctx.assistant.linked_connectors[0]
            if first_connector.connector_type != "local_file":
                return False, None

            doc_repo = DocumentRepository(ctx.db)
            docs = await doc_repo.get_by_connector(first_connector.id, limit=1)

            if not docs or not docs[0].file_metadata:
                return False, None

            ai_schema = docs[0].file_metadata.get("ai_schema")
            if not ai_schema or not ai_schema.get("filter_exact_cols"):
                return False, None

            return True, ai_schema
        except Exception as e:
            logger.error(f"CSV detection check failed: {e}")
            return False, None

    async def _prepare_csv_components(self, ctx: ChatContext) -> CSVComponents:
        """Initializes and returns typed pipeline components."""
        settings = ctx.settings_service
        provider = ctx.assistant.model_provider

        # Parallel Settings Fetch for fallback (Embedding)
        # Note: ChatEngineFactory now handles fetching API key/Model for LLM internally.

        # Use centralized Factory to get the correctly configured Chat Engine
        from app.factories.chat_engine_factory import ChatEngineFactory

        llm = await ChatEngineFactory.create_from_assistant(
            ctx.assistant, ctx.settings_service, temperature=ctx.assistant.configuration.get("temperature", 0.7)
        )

        # P0 FIX: Use the connector's ai_provider for collection name
        # The collection is determined by which embedding model was used during ingestion
        connector = next((c for c in ctx.assistant.linked_connectors if c.connector_type == "csv"), None)
        if not connector and ctx.assistant.linked_connectors:
            connector = ctx.assistant.linked_connectors[0]

        # Extract ai_provider from connector configuration, fallback to global setting
        if connector and connector.configuration.get("ai_provider"):
            embedding_provider = connector.configuration.get("ai_provider")
        else:
            embedding_provider = await settings.get_value("embedding_provider", default="local")

        col_name = await ctx.vector_service.get_collection_name(embedding_provider)

        # Fallback Embedding Strategy
        try:
            embed = await ctx.vector_service.get_embedding_model()
        except Exception:
            logger.warning("Falling back to local embeddings")
            embed = await ctx.vector_service.get_embedding_model(
                model_kwargs={"local_files_only": True}, provider="local"
            )

        qdrant_client = ctx.vector_service.get_qdrant_client()
        vector_store = QdrantVectorStore(
            collection_name=col_name, client=qdrant_client, aclient=ctx.vector_service.get_async_qdrant_client()
        )
        vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed)

        return CSVComponents(
            llm=llm,
            embed_model=embed,
            qdrant_client=qdrant_client,
            collection_name=col_name,
            vector_index=vector_index,
            retrieval_service=CSVRetrievalService(vector_index, qdrant_client, col_name),
        )

    def _format_error(self, message: str) -> str:
        return json.dumps({"type": KEY_ERROR, "message": message}, default=str) + "\n"

    def _yield_token_message(self, ctx: ChatContext, message: str) -> str:
        ctx.full_response_text = message
        return self._format_token(message)

    def _format_token(self, content: str) -> str:
        """Standard token format for frontend display."""
        return json.dumps({"type": "token", "content": content}, default=str) + "\n"

    async def _consume_with_timeout(self, generator, timeout):
        iterator = generator.__aiter__()
        while True:
            try:
                yield await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                raise
