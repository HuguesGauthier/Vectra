import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.core.ingestion.extractors import ComboMetadataExtractor, MetadataFormatter, NodeMetadata
from llama_index.core.schema import TextNode


@pytest.fixture
def mock_llm():
    return AsyncMock()


@pytest.fixture
def nodes():
    return [
        TextNode(
            text="This is a long enough text for extraction to happen. It needs to be more than 50 chars.", metadata={}
        ),
        TextNode(text="Short", metadata={}),
        TextNode(text="Another sufficiently long text for the third node in our parallel test suite.", metadata={}),
    ]


@pytest.mark.asyncio
async def test_combo_metadata_extractor_acall(mock_llm, nodes):
    extractor = ComboMetadataExtractor(llm=mock_llm)

    # Mock LLM program output
    mock_metadata = NodeMetadata(title="Test Title", summary="Test Summary", questions=["Q1?", "Q2?", "Q3?"])
    extractor.extraction_program = AsyncMock()
    extractor.extraction_program.acall.return_value = mock_metadata

    enriched_nodes = await extractor.acall(nodes)

    assert len(enriched_nodes) == 3
    # Node 0 and 2 should be enriched
    assert enriched_nodes[0].metadata["extracted_title"] == "Test Title"
    assert enriched_nodes[2].metadata["extracted_title"] == "Test Title"
    # Node 1 is short, should be skipped
    assert "extracted_title" not in enriched_nodes[1].metadata


@pytest.mark.asyncio
async def test_combo_metadata_extractor_error_fallback(mock_llm):
    node = TextNode(text="Valid length but extraction will fail because of the mock.")
    extractor = ComboMetadataExtractor(llm=mock_llm)
    extractor.extraction_program = AsyncMock()
    extractor.extraction_program.acall.side_effect = Exception("LLM Error")

    enriched_nodes = await extractor.acall([node])

    # Should fallback gracefully
    assert len(enriched_nodes) == 1
    assert "extracted_title" not in enriched_nodes[0].metadata


def test_metadata_formatter():
    formatter = MetadataFormatter()
    node = TextNode(
        text="Content",
        metadata={"extracted_title": "T", "extracted_summary": "S", "extracted_questions": ["Q1", "Q2", "Q3"]},
    )

    formatted_nodes = formatter([node])

    assert "smart_metadata" in formatted_nodes[0].metadata
    assert "TITRE: T" in formatted_nodes[0].metadata["smart_metadata"]
    # Check exclusion logic
    assert "extracted_title" in formatted_nodes[0].excluded_embed_metadata_keys
    assert "smart_metadata" not in formatted_nodes[0].excluded_embed_metadata_keys
