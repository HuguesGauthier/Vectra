import logging
from typing import Any, AsyncGenerator, List, Optional

from app.core.rag.processors import (BaseProcessor, QueryRewriterProcessor,
                                     RerankingProcessor, RetrievalProcessor,
                                     SynthesisProcessor,
                                     VectorizationProcessor)
from app.core.rag.types import PipelineContext, PipelineEvent

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Orchestrator for the RAG Process.
    Composes processors and manages the execution flow.
    """

    def __init__(
        self,
        llm: Any = None,
        embed_model: Any = None,
        search_strategy: Any = None,
        assistant: Any = None,
        chat_history: List[Any] = None,
        language: str = "en",
        # New optional args for flexible orchestration
        context: Optional[PipelineContext] = None,
        processors: Optional[List[BaseProcessor]] = None,
    ):
        if context:
            self.ctx = context
        else:
            self.ctx = PipelineContext(
                user_message="",
                chat_history=chat_history or [],
                language=language,
                assistant=assistant,
                llm=llm,
                embed_model=embed_model,
                search_strategy=search_strategy,
            )

        # Define Pipeline Strategy
        if processors:
            self.processors = processors
        else:
            self.processors = [
                QueryRewriterProcessor(),
                VectorizationProcessor(),
                RetrievalProcessor(),
                RerankingProcessor(),
                SynthesisProcessor(),
            ]

    async def run(self, user_message: str) -> AsyncGenerator[PipelineEvent, None]:
        """
        Execute the pipeline with the given message.
        """
        self.ctx.user_message = user_message

        try:
            for processor in self.processors:
                async for event in processor.process(self.ctx):
                    yield event
        except Exception as e:
            logger.error(f"❌ RAG Pipeline Failed: {e}", exc_info=True)
            yield PipelineEvent(type="error", status="failed", payload=str(e))
