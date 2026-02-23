"""
Schema Mapper
=============
Responsible for translating internal `IndexingStrategy` (Ingestion Schema)
into LlamaIndex's `VectorStoreInfo` (LLM-facing Schema).

This is the bridge that tells the LLM:
"Here are the fields you can filter on in this collection."
"""

from typing import List, Optional

from llama_index.core.vector_stores.types import MetadataInfo, VectorStoreInfo

from app.schemas.ingestion import IndexingStrategy

# Constants
DEFAULT_DESCRIPTION = "A collection of smart records from CSV/Excel files."
TYPE_KEYWORD = "keyword"
TYPE_FLOAT = "float"
TYPE_INTEGER = "integer"
FIELD_YEARS_COVERED = "years_covered"
FIELD_FILE_NAME = "file_name"


class SchemaMapper:
    """
    Static utility for Schema Translation.
    Pure logic, no side effects.

    Responsibilities (SRP):
    1. Exact Match Mapping (Strings/Categories).
    2. Range Match Mapping (Numbers/Prices).
    3. Special Logic Mapping (Years, Metadata).
    """

    @staticmethod
    def map_to_vector_store_info(
        strategy: IndexingStrategy, collection_name: str, description: str = DEFAULT_DESCRIPTION
    ) -> VectorStoreInfo:
        """
        Converts internal strategy to LlamaIndex Metadata Info.
        """
        metadata_info_list: List[MetadataInfo] = []

        # 1. Map Exact Filters
        SchemaMapper._map_exact_filters(strategy, metadata_info_list)

        # 2. Map Range Filters
        SchemaMapper._map_range_filters(strategy, metadata_info_list)

        # 3. Map Special Logic (Years)
        SchemaMapper._map_special_filters(strategy, metadata_info_list)

        # 4. Map Standard Metadata
        SchemaMapper._map_standard_metadata(metadata_info_list)

        return VectorStoreInfo(content_info=description, metadata_info=metadata_info_list)

    # --- Private Atomized Logic ---

    @staticmethod
    def _map_exact_filters(strategy: IndexingStrategy, info_list: List[MetadataInfo]) -> None:
        """Maps categorical/exact match columns."""
        for col in strategy.filter_exact_cols:
            info_list.append(
                MetadataInfo(
                    name=col,
                    type=TYPE_KEYWORD,
                    description=f"Filter by {col} (Exact Match). Use this for categorical fields like ID, Make, Model.",
                )
            )

    @staticmethod
    def _map_range_filters(strategy: IndexingStrategy, info_list: List[MetadataInfo]) -> None:
        """Maps numerical/range columns."""
        for col in strategy.filter_range_cols:
            info_list.append(
                MetadataInfo(
                    name=col,
                    type=TYPE_FLOAT,  # Float handles ints too usually
                    description=f"Filter by {col} (Numerical Range). Use for prices, dimensions, etc.",
                )
            )

    @staticmethod
    def _map_special_filters(strategy: IndexingStrategy, info_list: List[MetadataInfo]) -> None:
        """Maps complex/computed filters like Years Covered."""
        if hasattr(strategy, "start_year_col") and strategy.start_year_col and strategy.end_year_col:
            info_list.append(
                MetadataInfo(
                    name=FIELD_YEARS_COVERED,
                    type=TYPE_INTEGER,
                    description=(
                        "List of years compatible with the item. "
                        "CRITICAL: Use this filter when the user mentions a specific year (e.g. '2015'). "
                        "Do NOT use year_start/year_end unless explicitly asked for a range bound."
                    ),
                )
            )

    @staticmethod
    def _map_standard_metadata(info_list: List[MetadataInfo]) -> None:
        """Adds always-present system metadata."""
        info_list.append(
            MetadataInfo(name=FIELD_FILE_NAME, type=TYPE_KEYWORD, description="The name of the source file.")
        )
