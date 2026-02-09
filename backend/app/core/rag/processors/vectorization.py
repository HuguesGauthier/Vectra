import logging
from typing import AsyncGenerator

from llama_index.core.schema import QueryBundle

from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent

logger = logging.getLogger(__name__)


class VectorizationProcessor(BaseProcessor):
    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        yield PipelineEvent(type="step", step_type="vectorization", status="running")
        try:
            query = ctx.rewritten_query or ctx.user_message
            query_embedding = await ctx.embed_model.aget_query_embedding(query)
            ctx.query_bundle = QueryBundle(query_str=query, embedding=query_embedding)
            yield PipelineEvent(
                type="step", step_type="vectorization", status="completed", payload={"embedding": query_embedding}
            )
        except Exception as e:
            logger.error(f"Vectorization failed: {e}")
            raise e
