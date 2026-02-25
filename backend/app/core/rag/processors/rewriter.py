import logging
from typing import AsyncGenerator

from app.core.prompts import REWRITE_QUESTION_PROMPT
from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from app.core.rag.utils import estimate_tokens

logger = logging.getLogger(__name__)


class QueryRewriterProcessor(BaseProcessor):
    """
    Processor responsible for rewriting the user query based on chat history.
    Uses LLM to generate a standalone question that captures conversational context.
    """

    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:

        # OPTIMIZATION: Skip rewriting if no meaningful history (saves ~4s per query)
        # Rewriting is only useful when there's conversational context
        if not ctx.chat_history or len(ctx.chat_history) < 3:
            ctx.rewritten_query = ctx.user_message
            logger.debug("Skipping query rewrite (insufficient history)")
            return

        yield PipelineEvent(type="step", step_type="query_rewrite", status="running")
        try:
            history_str = "\n".join([f"{m.role}: {m.content}" for m in ctx.chat_history[-3:]])
            prompt = REWRITE_QUESTION_PROMPT.format(chat_history=history_str, question=ctx.user_message)

            # Estimate input tokens
            input_tokens = estimate_tokens(prompt)

            resp = await ctx.llm.acomplete(prompt)
            ctx.rewritten_query = resp.text.strip()

            # Estimate output tokens
            output_tokens = estimate_tokens(ctx.rewritten_query)

            logger.debug(f"Rewritten Question: {ctx.rewritten_query}")
            yield PipelineEvent(
                type="step",
                step_type="query_rewrite",
                status="completed",
                payload={"query": ctx.rewritten_query, "tokens": {"input": input_tokens, "output": output_tokens}},
            )
        except Exception as e:
            logger.warning(f"Rewrite failed (falling back to original): {e}")
            ctx.rewritten_query = ctx.user_message
            yield PipelineEvent(
                type="step", step_type="query_rewrite", status="completed", payload={"query": ctx.rewritten_query}
            )
