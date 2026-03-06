import json
import logging
from typing import Any, Dict, List

from llama_index.core.program import LLMTextCompletionProgram
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Node(BaseModel):
    id: str = Field(description="Unique identifier for the node, e.g., 'person_123'")
    label: str = Field(description="Label or semantic category of the node, e.g., 'Person', 'Organization', 'Event'")
    properties: Dict[str, Any] = Field(description="Key-value properties of the node")


class Relationship(BaseModel):
    source: str = Field(description="ID of the source node")
    target: str = Field(description="ID of the target node")
    type: str = Field(description="Type of the relationship, UPPER_SNAKE_CASE, e.g., 'WORKS_FOR'")
    properties: Dict[str, Any] = Field(description="Key-value properties of the relationship")


class GraphExtractionResult(BaseModel):
    nodes: List[Node] = Field(description="Extracted entities as nodes")
    relationships: List[Relationship] = Field(description="Extracted connections as relationships between nodes")


GRAPH_EXTRACTION_PROMPT = """
You are an expert graph data modeler.
Given the following batch of CSV records, extract meaningful entities as nodes and relationships between them.

INSTRUCTIONS:
- Each node must have a unique 'id' that is consistent across the result so relationships can link them.
- Use generic but descriptive labels for nodes (e.g., 'Person', 'Company', 'Product', 'Location', 'Event').
- Use UPPER_SNAKE_CASE for relationship types (e.g., 'WORKS_FOR', 'PURCHASED').
- Include relevant properties for both nodes and relationships. Do not duplicate the ID or label in the properties.
- Ensure the result matches the defined schema perfectly.

RECORDS:
{records_str}
"""


class GraphTransformer:
    """
    Takes batches of CSV records and asks an LLM to extract a graph representation.
    """

    def __init__(self, llm: Any):
        self.llm = llm
        self.extraction_program = LLMTextCompletionProgram.from_defaults(
            output_cls=GraphExtractionResult, prompt_template_str=GRAPH_EXTRACTION_PROMPT, llm=self.llm, verbose=False
        )

    async def extract_graph_from_batch(self, records: List[Dict[str, Any]]) -> GraphExtractionResult:
        """
        Takes a list of record dictionaries and requests a structured graph extraction from the LLM.
        """
        if not records:
            return GraphExtractionResult(nodes=[], relationships=[])

        # Format records for the LLM prompt
        records_str = ""
        for idx, r in enumerate(records):
            records_str += f"Record {idx + 1}:\n{json.dumps(r, ensure_ascii=False, indent=2)}\n\n"

        import time

        start_t = time.time()
        try:
            logger.info(f"🕸️ Calling LLM for graph extraction ({len(records)} records)...")
            result: GraphExtractionResult = await self.extraction_program.acall(records_str=records_str)
            duration = time.time() - start_t
            logger.info(
                f"✅ Extracted {len(result.nodes)} nodes and {len(result.relationships)} relationships in {duration:.2f}s."
            )
            return result
        except Exception as e:
            logger.error(f"❌ Failed to extract graph from batch: {e}")
            return GraphExtractionResult(nodes=[], relationships=[])
