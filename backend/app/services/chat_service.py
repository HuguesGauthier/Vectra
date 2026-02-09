import json
import logging
import time
from typing import Annotated, AsyncGenerator, List, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.database import get_db
from app.models.assistant import Assistant
from app.repositories.chat_history_repository import (
    ChatPostgresRepository, get_chat_postgres_repository)
from app.schemas.chat import Message
from app.services.cache_service import SemanticCacheService, get_cache_service
from app.services.chat.chat_metrics_manager import ChatMetricsManager
from app.services.chat.processors.agentic_processor import AgenticProcessor
from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.processors.history_processor import \
    HistoryLoaderProcessor
from app.services.chat.processors.persistence_processor import (
    AssistantPersistenceProcessor, UserPersistenceProcessor)
from app.services.chat.processors.rag_processor import RAGGenerationProcessor
from app.services.chat.processors.semantic_cache_processor import \
    SemanticCacheProcessor
from app.services.chat.processors.trending_processor import TrendingProcessor
from app.services.chat.processors.visualization_processor import \
    VisualizationProcessor
# Pipeline Imports
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter
from app.services.chat_history_service import (ChatHistoryService,
                                               get_chat_history_service)
from app.services.query_engine_factory import (UnifiedQueryEngineFactory,
                                               get_query_engine_factory)
from app.services.settings_service import SettingsService, get_settings_service
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)

# Constants
MSG_SESSION_REQUIRED = "Session ID is required."
MSG_MESSAGE_REQUIRED = "Message cannot be empty."
LOG_RESET_START = "🗑️  Resetting conversation for session: %s"
LOG_RESET_COMPLETE = "🎉 Conversation reset complete for session: %s"
LOG_REDIS_CLEARED = "✅ Redis history cleared for session: %s"
LOG_PG_CLEARED = "✅ Postgres history cleared for session: %s"
LOG_PG_EMPTY = "⚠️  No Postgres records found for session: %s"
ERR_REDIS_FAIL = "❌ Failed to clear Redis history for %s: %s"
ERR_PG_FAIL = "❌ Failed to clear Postgres history for %s: %s"
LOG_PIPELINE_START = "➡️  Pipeline: Running %s..."
LOG_PIPELINE_END = "✅ Pipeline: Finished %s"
ERR_CRITICAL_PIPELINE = "Critical Pipeline Error in session %s: %s"
DEFAULT_LANGUAGE = "en"


class ChatService:
    """
    Orchestrator for the Chat Pipeline.
    Manages the sequence of processors and handles conversation lifecycle.
    """

    def __init__(
        self,
        db: AsyncSession,
        vector_service: VectorService,
        settings_service: SettingsService,
        chat_history_service: ChatHistoryService,
        query_engine_factory: UnifiedQueryEngineFactory,
        chat_repository: ChatPostgresRepository,
        cache_service: Optional[SemanticCacheService] = None,
        trending_service_enabled: bool = False,
    ):
        """
        Initializes the ChatService with necessary dependencies.

        Args:
            db (AsyncSession): Database session.
            vector_service (VectorService): Service for vector operations.
            settings_service (SettingsService): Application settings service.
            chat_history_service (ChatHistoryService): Service for chat history (Redis).
            query_engine_factory (UnifiedQueryEngineFactory): Factory for query engines.
            chat_repository (ChatPostgresRepository): Repository for persistent chat storage.
            cache_service (Optional[SemanticCacheService]): Service for semantic caching.
            trending_service_enabled (bool): Flag to enable trending analysis.
        """
        self.db = db
        self.settings_service = settings_service
        self.vector_service = vector_service
        self.chat_history_service = chat_history_service
        self.query_engine_factory = query_engine_factory
        self.chat_repository = chat_repository
        self.cache_service = cache_service
        self.trending_service_enabled = trending_service_enabled

    async def reset_conversation(self, session_id: str) -> None:
        """
        Reset conversation by clearing both Redis (hot storage) and Postgres (audit log).

        Args:
            session_id (str): The unique identifier of the chat session.

        Raises:
            ValueError: If session_id is empty.
        """
        self._validate_session_id(session_id)

        logger.info(LOG_RESET_START, session_id)

        await self._clear_hot_storage(session_id)
        # P0 FIX: User requested to KEEP audit history in DB even on reset.
        # Only Redis (context) is cleared. Old messages remain in Postgres for 1 year (Purge Policy).
        # await self._clear_cold_storage(session_id)

        logger.info(LOG_RESET_COMPLETE, session_id)

    async def stream_chat(
        self,
        message: str,
        assistant: Assistant,
        session_id: str,
        language: str = DEFAULT_LANGUAGE,
        history: Optional[List[Message]] = None,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Orchestrate the Chat Pipeline from start to finish.

        Args:
            message (str): The user's input message.
            assistant (Assistant): The assistant configuration.
            session_id (str): The active session ID.
            language (str): Language code (e.g., 'en', 'fr').
            history (Optional[List[Message]]): Previous chat history.
            user_id (Optional[str]): The user's ID.

        Yields:
            str: JSON strings representing pipeline events or errors.
        """
        self._validate_stream_inputs(message, session_id)

        start_time = time.time()
        ctx_metrics = self._initialize_metrics_manager()

        # 0. Initialize Pipeline Event
        yield await self._emit_initialization_event(ctx_metrics, language)

        try:
            # 1. Prepare Data & Context
            init_span = ctx_metrics.start_span(PipelineStepType.INITIALIZATION)

            prepared_assistant = await self._load_and_detach_assistant(assistant.id)

            ctx = self._create_context(
                session_id=session_id,
                message=message,
                assistant=prepared_assistant,
                language=language,
                history=history,
                user_id=user_id,
                metrics_manager=ctx_metrics,
            )

            processors = self._get_processors_chain()

            # End Initialization Metrics
            init_metric = ctx.metrics.end_span(init_span)
            yield EventFormatter.format(
                PipelineStepType.INITIALIZATION, StepStatus.COMPLETED, language, duration=init_metric.duration
            )

            # 2. Execute Pipeline
            async for chunk in self._execute_pipeline(processors, ctx):
                yield chunk

            # 3. Final Completion Event
            total_duration = round(time.time() - start_time, 3)
            yield EventFormatter.format(
                PipelineStepType.COMPLETED, StepStatus.COMPLETED, language, duration=total_duration
            )

        except Exception as e:
            # Catch-all for top-level safety to prevent stream disconnection
            yield self._handle_pipeline_error(session_id, e)

    # --- Private Helpers: Validation ---

    def _validate_session_id(self, session_id: str) -> None:
        if not session_id:
            raise ValueError(MSG_SESSION_REQUIRED)

    def _validate_stream_inputs(self, message: str, session_id: str) -> None:
        if not message:
            raise ValueError(MSG_MESSAGE_REQUIRED)
        self._validate_session_id(session_id)

    # --- Private Helpers: Reset Logic ---

    async def _clear_hot_storage(self, session_id: str) -> None:
        """Clears the session history from Redis."""
        try:
            await self.chat_history_service.clear_history(session_id)
            logger.info(LOG_REDIS_CLEARED, session_id)
        except Exception as e:
            logger.error(ERR_REDIS_FAIL, session_id, e)
            raise

    async def _clear_cold_storage(self, session_id: str) -> None:
        """Clears the session history from Postgres."""
        try:
            deleted = await self.chat_repository.clear_history(session_id)
            if deleted:
                logger.info(LOG_PG_CLEARED, session_id)
            else:
                logger.warning(LOG_PG_EMPTY, session_id)
        except Exception as e:
            logger.error(ERR_PG_FAIL, session_id, e)
            raise

    # --- Private Helpers: Pipeline Setup ---

    def _initialize_metrics_manager(self) -> ChatMetricsManager:
        """Initializes the metrics manager for the request."""
        return ChatMetricsManager()

    async def _emit_initialization_event(self, metrics: ChatMetricsManager, language: str) -> str:
        """Emits the first event of the stream."""
        return EventFormatter.format(PipelineStepType.INITIALIZATION, StepStatus.RUNNING, language)

    async def _load_and_detach_assistant(self, assistant_id: str) -> Assistant:
        """
        Fetches and detaches the assistant from the session to avoid Greenlet errors.
        Eager loads 'linked_connectors' so they are available after detachment.
        """
        stmt = select(Assistant).options(selectinload(Assistant.linked_connectors)).where(Assistant.id == assistant_id)
        result = await self.db.execute(stmt)
        refreshed_assistant = result.scalar_one()

        # Expunge to detach from the async session
        self.db.expunge(refreshed_assistant)
        return refreshed_assistant

    def _create_context(
        self,
        session_id: str,
        message: str,
        assistant: Assistant,
        language: str,
        history: Optional[List[Message]],
        user_id: Optional[str],
        metrics_manager: ChatMetricsManager,
    ) -> ChatContext:
        """Constructs the ChatContext object."""
        ctx = ChatContext(
            session_id=session_id,
            message=message,
            original_message=message,
            assistant=assistant,
            language=language,
            db=self.db,
            settings_service=self.settings_service,
            vector_service=self.vector_service,
            chat_history_service=self.chat_history_service,
            query_engine_factory=self.query_engine_factory,
            cache_service=self.cache_service,
            trending_enabled=self.trending_service_enabled,
            history=history or [],
            user_id=user_id,
        )
        ctx.metrics = metrics_manager
        return ctx

    def _get_processors_chain(self) -> List[BaseChatProcessor]:
        """Instantiates the sequence of processors for the pipeline."""
        return [
            HistoryLoaderProcessor(),
            SemanticCacheProcessor(),
            UserPersistenceProcessor(),
            AgenticProcessor(),
            RAGGenerationProcessor(),
            VisualizationProcessor(),
            TrendingProcessor(),  # Moved before persistence
            AssistantPersistenceProcessor(),  # Must be LAST to capture all steps
        ]

    # --- Private Helpers: Execution ---

    async def _execute_pipeline(
        self, processors: List[BaseChatProcessor], ctx: ChatContext
    ) -> AsyncGenerator[str, None]:
        """Iterates through processors and yields their output."""
        for processor in processors:
            name = processor.__class__.__name__
            logger.info(LOG_PIPELINE_START, name)

            async for chunk in processor.process(ctx):
                if chunk:
                    yield chunk

            logger.info(LOG_PIPELINE_END, name)

    def _handle_pipeline_error(self, session_id: str, error: Exception) -> str:
        """Logs the critical error and returns a friendly JSON error message."""
        logger.error(ERR_CRITICAL_PIPELINE, session_id, error, exc_info=True)
        return json.dumps({"type": "error", "message": "An unexpected error occurred. Please try again."}) + "\n"


async def get_chat_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    query_engine_factory: Annotated[UnifiedQueryEngineFactory, Depends(get_query_engine_factory)],
    chat_history_service: Annotated[ChatHistoryService, Depends(get_chat_history_service)],
    chat_repository: Annotated[ChatPostgresRepository, Depends(get_chat_postgres_repository)],
    cache_service: Annotated[Optional[SemanticCacheService], Depends(get_cache_service)],
) -> ChatService:
    """Dependency Provider for ChatService."""
    return ChatService(
        db=db,
        vector_service=vector_service,
        settings_service=settings_service,
        chat_history_service=chat_history_service,
        query_engine_factory=query_engine_factory,
        chat_repository=chat_repository,
        cache_service=cache_service,
        trending_service_enabled=True,  # Consider configuring this via settings
    )
