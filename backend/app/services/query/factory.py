"""
Dynamic Retriever Factory
=========================
Constructs the optimal Retriever logic based on available Schema.

Factories:
- Standard K-NN: Default fallback.
- Auto-Retriever: Smart Filtering based on Schema (requires LLM).
"""

import logging
from typing import Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.llms import LLM
from llama_index.core.retrievers import BaseRetriever, VectorIndexAutoRetriever

from app.schemas.ingestion import IndexingStrategy
from app.services.query.schema_mapper import SchemaMapper

logger = logging.getLogger(__name__)

# Constants
DEFAULT_SIMILARITY_TOP_K: int = 5
MAX_AUTO_RETRIEVER_TOP_K: int = 100
DEFAULT_COLLECTION_NAME: str = "default_collection"


class DynamicRetrieverFactory:
    """
    Factory for instantiating Retrievers.

    Responsibilities (SRP):
    1. Logic Selection (Standard vs Auto).
    2. Component Instantiation (Safe Construction).
    3. Fallback Management.
    """

    @staticmethod
    def get_retriever(
        index: VectorStoreIndex,
        indexing_strategy: Optional[IndexingStrategy] = None,
        llm: Optional[LLM] = None,
        similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> BaseRetriever:
        """
        Factory method to get the best retriever for the job.

        Args:
            index: The VectorStoreIndex to retrieve from.
            indexing_strategy: Optional schema/strategy definition.
            llm: LLM instance (required for AutoRetriever).
            similarity_top_k: Number of results to return.
            collection_name: Target collection name.

        Returns:
            A configured BaseRetriever instance.
        """
        factory = DynamicRetrieverFactory

        # 1. Decision Logic
        if not indexing_strategy:
            logger.info("🔍 Query Factory: Using Standard Vector Retriever (No Schema)")
            return factory._create_standard_retriever(index, similarity_top_k)

        if not llm:
            logger.warning("⚠️ Query Factory: Strategy present but no LLM provided. Falling back to Standard.")
            return factory._create_standard_retriever(index, similarity_top_k)

        # 2. Advanced Construction (Auto-Retriever)
        return factory._create_auto_retriever(index, indexing_strategy, llm, similarity_top_k, collection_name)

    # --- Private Factories ---

    @staticmethod
    def _create_standard_retriever(index: VectorStoreIndex, top_k: int) -> BaseRetriever:
        """Creates a basic K-NN retriever."""
        return index.as_retriever(similarity_top_k=top_k)

    @staticmethod
    def _create_auto_retriever(
        index: VectorStoreIndex, strategy: IndexingStrategy, llm: LLM, top_k: int, collection_name: str
    ) -> BaseRetriever:
        """Creates a smart AutoRetriever with filters."""
        try:
            logger.info("🧠 Query Factory: Constructing AutoRetriever (Smart Filtering)")

            # Map Strategy -> VectorStoreInfo
            vector_store_info = SchemaMapper.map_to_vector_store_info(
                strategy=strategy, collection_name=collection_name
            )

            return VectorIndexAutoRetriever(
                index,
                vector_store_info=vector_store_info,
                llm=llm,
                similarity_top_k=top_k,
                verbose=True,  # Log the generated filters
                max_top_k=MAX_AUTO_RETRIEVER_TOP_K,
            )

        except Exception as e:
            logger.error(f"❌ Query Factory: Failed to create AutoRetriever: {e}. Falling back to Standard.")
            return DynamicRetrieverFactory._create_standard_retriever(index, top_k)
