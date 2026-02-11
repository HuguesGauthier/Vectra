import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.visualization_service import VisualizationService, VizDataInfo
from app.services.chat.types import ChatContext


@pytest.fixture
def service():
    return VisualizationService()


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=ChatContext)
    ctx.message = "Show me a chart"
    ctx.retrieved_sources = []
    ctx.full_response_text = ""
    ctx.sql_results = None
    ctx.assistant = MagicMock()
    ctx.settings_service = MagicMock()
    return ctx


@pytest.mark.asyncio
async def test_extract_from_sql(service, mock_ctx):
    # Setup
    mock_ctx.sql_results = [{"Month": "Jan", "Revenue": 1000}, {"Month": "Feb", "Revenue": 1200}]
    mock_ctx.full_response_text = "Here is the revenue in $"

    # Execute
    info = await service.extract_data_info(mock_ctx)

    # Assert
    assert info.row_count == 2
    assert info.columns == ["Month", "Revenue"]
    assert info.sample_data[0] == ["Jan", 1000]
    assert info.has_numeric is True
    assert info.is_currency is True


@pytest.mark.asyncio
async def test_classify_guardrail_non_numeric(service, mock_ctx):
    # Setup
    data = VizDataInfo(
        row_count=2,
        columns=["Name", "Status"],
        sample_data=[["Item A", "Active"], ["Item B", "Pending"]],
        has_numeric=False,
    )

    # Execute
    viz_type, tokens = await service.classify_visualization_type(mock_ctx, data)

    # Assert
    assert viz_type == "table"
    assert tokens == {"input": 0, "output": 0}


@pytest.mark.asyncio
async def test_regex_extraction_genui(service, mock_ctx):
    # Setup
    mock_ctx.full_response_text = """
    Check this data:
    :::table {
        "columns": [{"name": "product", "label": "Product"}, {"name": "price", "label": "Price"}],
        "data": [{"product": "Phone", "price": "500"}, {"product": "Laptop", "price": "1000"}]
    } :::
    """

    # Execute
    info = await service.extract_data_info(mock_ctx)

    # Assert
    assert info.row_count == 2
    assert info.columns == ["Product", "Price"]
    assert info.sample_data[0] == ["Phone", "500"]
    assert info.has_numeric is True


@pytest.mark.asyncio
async def test_format_cartesian_bar(service, mock_ctx):
    # Setup
    data = VizDataInfo(
        row_count=2, columns=["Month", "Sales"], sample_data=[["Jan", 100], ["Feb", 150]], has_numeric=True
    )

    # Execute
    result = service.format_visualization_data(mock_ctx, "bar", data)

    # Assert
    assert result["viz_type"] == "bar"
    assert result["series"][0]["name"] == "Sales"
    assert result["series"][0]["data"] == [100.0, 150.0]
    assert result["chartOptions"]["xaxis"]["categories"] == ["Jan", "Feb"]


@pytest.mark.asyncio
async def test_classify_with_llm(service, mock_ctx):
    # Setup
    data = VizDataInfo(row_count=5, columns=["Category", "Value"], sample_data=[["A", 10], ["B", 20]], has_numeric=True)

    mock_response = MagicMock()
    mock_response.text = "pie"
    mock_response.__str__.return_value = "pie"
    mock_response.raw = {"usage_metadata": {"prompt_token_count": 100, "candidates_token_count": 5}}

    with patch(
        "app.services.visualization_service.ChatEngineFactory.create_from_assistant", AsyncMock()
    ) as mock_factory:
        mock_llm = AsyncMock()
        mock_llm.acomplete.return_value = mock_response
        mock_factory.return_value = mock_llm

        # Execute
        viz_type, tokens = await service.classify_visualization_type(mock_ctx, data)

        # Assert
        assert viz_type == "pie"
        assert tokens["input"] == 100
        assert tokens["output"] == 5
