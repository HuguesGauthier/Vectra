import logging
from typing import AsyncGenerator, List, Dict, Any

from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from app.core.prompts import GRAPH_ENTITY_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class GraphRetrievalProcessor(BaseProcessor):
    """
    Processor responsible for retrieving relevant triplets from Neo4j.
    1. Extracts entities from the query using the LLM.
    2. Queries Neo4j for these entities and their immediate relationships.
    3. Adds the triplets to the pipeline context.
    """

    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        if not ctx.graph_service:
            logger.warning("GraphRetrievalProcessor: No graph_service available.")
            return

        yield PipelineEvent(
            type="step", step_type="graph_retrieval", status="running", label="Analyse des entités et du graphe..."
        )

        try:
            # 1. Entity Extraction
            query = ctx.rewritten_query or ctx.user_message
            prompt = GRAPH_ENTITY_EXTRACTION_PROMPT.format(query=query)

            # Simple LLM call for extraction
            response = await ctx.llm.acomplete(prompt)
            entities_raw = str(response).strip()
            entities = [e.strip() for e in entities_raw.split(",") if e.strip()]

            if not entities:
                logger.info("No entities extracted for graph search.")
                yield PipelineEvent(
                    type="step",
                    step_type="graph_retrieval",
                    status="completed",
                    label="Aucune entité trouvée pour le graphe.",
                )
                return

            logger.info(f"Extracted entities for graph search: {entities}")

            # 2. Neo4j Query (1-hop traversal for each entity)
            # We look for nodes that match the entity names (case-insensitive)
            # and retrieve their relationships.

            all_triplets = []
            for entity in entities:
                cypher = """
                MATCH (n:Entity)
                WHERE n.id =~ ('(?i).*' + $entity + '.*') OR n.name =~ ('(?i).*' + $entity + '.*')
                MATCH (n)-[r]-(m:Entity)
                RETURN 
                    n.id as source, 
                    type(r) as relationship, 
                    m.id as target, 
                    labels(n) as source_labels, 
                    labels(m) as target_labels,
                    properties(n) as source_props,
                    properties(m) as target_props,
                    properties(r) as rel_props
                LIMIT 20
                """
                results = await ctx.graph_service.execute_query(cypher, {"entity": entity})

                for res in results:
                    triplet = {
                        "source": res["source"],
                        "relationship": res["relationship"],
                        "target": res["target"],
                        "source_labels": res["source_labels"],
                        "target_labels": res["target_labels"],
                        "source_props": res["source_props"],
                        "target_props": res["target_props"],
                        "rel_props": res["rel_props"],
                    }
                    all_triplets.append(triplet)

            # Deduplicate triplets
            unique_triplets = []
            seen = set()
            for t in all_triplets:
                t_key = tuple(sorted([str(t["source"]), str(t["relationship"]), str(t["target"])]))
                if t_key not in seen:
                    seen.add(t_key)
                    unique_triplets.append(t)

            # 3. Store in Context
            ctx.graph_context = unique_triplets

            logger.info(f"Retrieved {len(unique_triplets)} triplets from Neo4j.")

            yield PipelineEvent(
                type="step",
                step_type="graph_retrieval",
                status="completed",
                label=f"Récupéré {len(unique_triplets)} relations du graphe.",
                payload={"triplet_count": len(unique_triplets)},
            )

        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}", exc_info=True)
            yield PipelineEvent(type="step", step_type="graph_retrieval", status="failed", payload={"error": str(e)})
            # Don't raise, let the pipeline continue with vector results
