import logging
from typing import AsyncGenerator

from llama_index.core.schema import NodeWithScore, TextNode

from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent

logger = logging.getLogger(__name__)


class RetrievalProcessor(BaseProcessor):
    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        yield PipelineEvent(type="step", step_type="retrieval", status="running")
        try:
            similarity_top_k = ctx.assistant.top_k_retrieval or 10

            # P0: Extract ACLs from Assistant Configuration
            # P0: Extract ACLs from Assistant Configuration
            # "configuration" is a dict stored in DB. Key is "tags" per Schema.
            acls = ctx.assistant.configuration.get("tags", [])
            if isinstance(acls, str):
                acls = [acls]  # Safety check

            # Create Filters
            from app.strategies.search.base import SearchFilters

            filters = SearchFilters(
                user_acl=acls if acls else None,
                assistant=ctx.assistant,  # Pass assistant for multi-collection resolution
            )

            query = ctx.rewritten_query or ctx.user_message
            search_results = await ctx.search_strategy.search(query=query, top_k=similarity_top_k, filters=filters)

            nodes = []
            retrieved_doc_ids = []
            for res in search_results:
                # TextNode expects metadata as dict, not Pydantic model
                metadata_dict = res.metadata.model_dump() if hasattr(res.metadata, "model_dump") else res.metadata
                text_node = TextNode(text=res.content, metadata=metadata_dict)
                nodes.append(NodeWithScore(node=text_node, score=res.score))

                # Track document ID for utilization analytics
                doc_id = metadata_dict.get("document_id") or metadata_dict.get("file_path")
                if doc_id:
                    retrieved_doc_ids.append(str(doc_id))

            # P0: Dual Threshold Strategy - Vector Cutoff
            # Filter low-quality vector matches early to reduce noise before Reranking
            retrieval_cutoff = getattr(ctx.assistant, "retrieval_similarity_cutoff", 0.5)

            original_count = len(nodes)
            nodes = [n for n in nodes if (n.score or 0) >= retrieval_cutoff]
            filtered_count = original_count - len(nodes)

            if filtered_count > 0:
                logger.info(f"[RETRIEVAL] Filtered {filtered_count} nodes below vector threshold {retrieval_cutoff}")

            yield PipelineEvent(
                type="step",
                step_type="retrieval",
                status="completed",
                label=f"Retrieved {len(nodes)} documents (Filtered {filtered_count})",
            )

            # CRITICAL FIX: Pass nodes to next processor
            ctx.retrieved_nodes = nodes

            # Store for analytics tracking
            if retrieved_doc_ids:
                ctx.metadata["retrieved_document_ids"] = retrieved_doc_ids

            # DO NOT emit sources here - RerankerProcessor will emit them after filtering

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            yield PipelineEvent(type="step", step_type="retrieval", status="failed", payload={"error": str(e)})
            raise e
