import json
import logging
from typing import AsyncGenerator

from llama_index.core import PromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

from app.core.prompts import RAG_ANSWER_PROMPT
from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from app.core.rag.utils import estimate_tokens

logger = logging.getLogger(__name__)


class SynthesisProcessor(BaseProcessor):
    """
    Processor responsible for synthesizing a final response from retrieved context nodes.
    Handles context cleaning, prompt formatting, and LLM streaming.
    """

    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        yield PipelineEvent(type="step", step_type="synthesis", status="running")

        cleaned_contexts = []
        for n in ctx.retrieved_nodes:
            raw_text = n.node.get_content()
            final_text = raw_text

            # Robust JSON cleaning (matching ChatService logic)
            if raw_text.strip().startswith("{"):
                try:
                    parsed = json.loads(raw_text)
                    if "text" in parsed:
                        final_text = parsed["text"]
                    elif "content" in parsed:
                        final_text = parsed["content"]
                    elif "_node_content" in parsed:
                        content_str = parsed["_node_content"]
                        if isinstance(content_str, str):
                            inner = json.loads(content_str)
                            final_text = inner.get("text", inner.get("content", raw_text))
                except Exception:
                    logger.debug("Failed to parse node content as JSON, using raw text.")

            cleaned_contexts.append(final_text)

        context_str = "\n\n".join(cleaned_contexts)

        # Format Chat History explicitly
        messages = []
        if ctx.assistant.instructions:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=ctx.assistant.instructions))

        for msg in ctx.chat_history:
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", None)
            if role and content:
                messages.append(ChatMessage(role=role, content=content))

        # Create final user message with context
        fmt = PromptTemplate(RAG_ANSWER_PROMPT)
        final_user_content = fmt.format(
            role_instruction="",  # Already in system prompt
            chat_history="",  # We passed history as messages
            context_str=context_str,
            query_str=ctx.user_message,
        )

        messages.append(ChatMessage(role=MessageRole.USER, content=final_user_content))

        try:
            # Estimate input tokens (rough)
            input_tokens = estimate_tokens(final_user_content)

            # Use Chat API with Tools
            stream_response = await ctx.llm.astream_chat(messages, tools=ctx.tools)
            yield PipelineEvent(type="response_stream", payload=stream_response)

            yield PipelineEvent(
                type="step",
                step_type="synthesis",
                status="completed",
                payload={"tokens": {"input": input_tokens, "output": 0}},
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            raise e
