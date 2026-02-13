"""
Smart Metadata Extraction for RAG Ingestion Pipeline.

Implements combo strategy: single LLM call extracts Title + Summary + Questions
to enrich document chunks with semantic metadata for improved retrieval.
"""

import asyncio
import logging
from typing import Any, List, Optional, Sequence

from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.schema import BaseNode, TransformComponent
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class NodeMetadata(BaseModel):
    """
    Structured metadata extracted from text chunks.
    All fields extracted in single LLM call (combo strategy).
    """

    title: str = Field(description="Un titre concis et descriptif pour ce segment de texte (max 10 mots)")
    summary: str = Field(description="Un résumé d'une phrase capturant l'essentiel du contenu")
    questions: List[str] = Field(
        description="3 questions stratégiques auxquelles ce texte peut répondre", min_length=3, max_length=3
    )


# French-optimized prompt template for technical documentation
EXTRACTION_PROMPT_FR = """
Analyse le texte suivant et extrais les métadonnées structurées.

TEXTE:
{text_chunk}

INSTRUCTIONS:
- Génère un titre concis et informatif (max 10 mots)
- Crée un résumé d'une phrase capturant l'essence du contenu
- Formule 3 questions stratégiques auxquelles ce texte répond

Réponds au format JSON strict suivant:
{{
    "title": "...",
    "summary": "...",
    "questions": ["Q1?", "Q2?", "Q3?"]
}}
"""


# English-optimized prompt template for technical documentation
EXTRACTION_PROMPT_EN = """
Analyze the following text and extract structured metadata.

TEXT:
{text_chunk}

INSTRUCTIONS:
- Generate a concise and informative title (max 10 words)
- Create a one-sentence summary capturing the essence of the content
- Formulate 3 strategic questions that this text answers

Answer in strict JSON format:
{{
    "title": "...",
    "summary": "...",
    "questions": ["Q1?", "Q2?", "Q3?"]
}}
"""


class ComboMetadataExtractor(TransformComponent):
    """
    Custom LlamaIndex transformer that enriches nodes with AI-extracted metadata.

    Uses LLMTextCompletionProgram to extract Title, Summary, and Questions in a
    single LLM call for efficiency.
    """

    llm: Any = Field(description="The LLM to use for extraction")
    extraction_model: str = Field(default="gemini-flash", description="Model identifier for logging")
    language: str = Field(default="fr", description="Language for extraction prompts (fr/en)")
    extraction_program: Optional[Any] = Field(default=None, description="Compiled LLM program")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, llm, extraction_model: str = "gemini-flash", language: str = "fr", **kwargs):
        super().__init__(llm=llm, extraction_model=extraction_model, language=language, **kwargs)

        # Select prompt based on language
        prompt_template = EXTRACTION_PROMPT_FR if language == "fr" else EXTRACTION_PROMPT_EN

        logger.info(f"✨ ComboMetadataExtractor initialized with model: {extraction_model} | Language: {language}")

        self.extraction_program = LLMTextCompletionProgram.from_defaults(
            output_cls=NodeMetadata, prompt_template_str=prompt_template, llm=self.llm, verbose=False
        )

    def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        """
        [Sync] Transform nodes by enriching with extracted metadata.
        Required by TransformComponent ABC.
        """
        enriched_nodes = []

        for i, node in enumerate(nodes):
            try:
                # Extract text content
                text_content = node.get_content()

                # Skip very short chunks
                if len(text_content) < 50:
                    enriched_nodes.append(node)
                    continue

                # Truncate
                text_for_extraction = text_content[:2000]

                # Call LLM program SYNC
                extracted_metadata = self.extraction_program(text_chunk=text_for_extraction)

                # Enrich
                if node.metadata is None:
                    node.metadata = {}

                node.metadata["extracted_title"] = extracted_metadata.title
                node.metadata["extracted_summary"] = extracted_metadata.summary
                node.metadata["extracted_questions"] = extracted_metadata.questions

                enriched_nodes.append(node)

            except Exception as e:
                logger.warning(f"⚠️ Metadata extraction failed for chunk {i}: {e}")
                enriched_nodes.append(node)

        return enriched_nodes

    async def acall(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        """
        [Async] Transform nodes by enriching with extracted metadata.
        Parallelized with Semaphore to respect rate limits.
        """
        # P1: Parallelize using Semaphore to avoid sequential bottleneck
        # Max 5 parallel extractions to respect LLM rate limits without being too slow
        semaphore = asyncio.Semaphore(5)

        async def _extract_single(i: int, node: BaseNode) -> BaseNode:
            async with semaphore:
                try:
                    text_content = node.get_content()

                    if len(text_content) < 50:
                        logger.debug(f"Skipping metadata extraction for short chunk {i} ({len(text_content)} chars)")
                        return node

                    text_for_extraction = text_content[:2000]

                    # LLM Call
                    extracted_metadata = await self.extraction_program.acall(text_chunk=text_for_extraction)

                    if node.metadata is None:
                        node.metadata = {}

                    node.metadata["extracted_title"] = extracted_metadata.title
                    node.metadata["extracted_summary"] = extracted_metadata.summary
                    node.metadata["extracted_questions"] = extracted_metadata.questions

                    logger.debug(f"✅ Extracted metadata for chunk {i}: title='{extracted_metadata.title[:30]}...'")
                    return node

                except Exception as e:
                    logger.warning(f"⚠️ Metadata extraction failed for chunk {i}: {str(e)}")
                    return node

        # Execute in parallel
        tasks = [_extract_single(i, node) for i, node in enumerate(nodes)]
        enriched_nodes = await asyncio.gather(*tasks)

        enriched_count = sum(1 for n in enriched_nodes if "extracted_title" in (n.metadata or {}))
        logger.info(
            f"🎯 Metadata extraction complete: {len(enriched_nodes)} chunks processed ({enriched_count} enriched)"
        )

        return enriched_nodes

    @classmethod
    def class_name(cls) -> str:
        """Required by TransformComponent interface."""
        return "ComboMetadataExtractor"


def format_embedding_metadata(metadata: dict) -> str:
    """
    Format metadata into a semantic string for the embedding model.
    """
    title = metadata.get("extracted_title", "N/A")
    summary = metadata.get("extracted_summary", "N/A")
    questions = metadata.get("extracted_questions", [])

    # Format questions list
    questions_str = "\n".join([f"- {q}" for q in questions]) if questions else "Aucune question"

    return f"""TITRE: {title}
RÉSUMÉ: {summary}
QUESTIONS PERTINENTES:
{questions_str}"""


class MetadataFormatter(TransformComponent):
    """
    Clean and format metadata before embedding.
    Ensures specific AI-generated fields are used for vectorization.
    """

    def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        for node in nodes:
            # 1. Generate Formatted Metadata Block
            # We pre-format the string here because LlamaIndex metadata_template
            # applies to all keys, and we want specific formatting for this block.
            formatted_metadata = format_embedding_metadata(node.metadata)

            # Store in a dedicated key that we will include
            node.metadata["smart_metadata"] = formatted_metadata

            # 2. Force Include Safety Logic
            # Ensure our new formatted key is INCLUDED
            if "smart_metadata" in node.excluded_embed_metadata_keys:
                node.excluded_embed_metadata_keys.remove("smart_metadata")

            # 3. Exclude Raw Fields (to avoid duplication and ensure clean format)
            # We exclude the raw extracted fields because they are now inside 'smart_metadata'
            for key in ["extracted_title", "extracted_summary", "extracted_questions"]:
                if key not in node.excluded_embed_metadata_keys:
                    node.excluded_embed_metadata_keys.append(key)

            # 4. Configure Template
            # We use a neutral template. The specific formatting is inside the values.
            # This fixes the ValidationError (was assigning a function instead of string)
            node.metadata_template = "{key}: {value}"
            node.metadata_seperator = "\n\n"

        return nodes

    @classmethod
    def class_name(cls) -> str:
        return "MetadataFormatter"
