import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.sql_discovery_service import SQLDiscoveryService, VannaQueryEngineWrapper
from app.schemas.enums import ConnectorType


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    service = AsyncMock()
    service.get_value.return_value = "mock-value"
    return service


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get_engine.return_value = None
    return cache


@pytest.fixture
def service(mock_db, mock_settings, mock_cache):
    return SQLDiscoveryService(mock_db, mock_settings, mock_cache)


def test_detect_db_type_postgres(service):
    config = {"host": "localhost", "port": 5432, "type": "postgresql"}
    driver, is_mssql, key, params, port = service._detect_db_type(config)
    assert driver == "postgresql"
    assert is_mssql is False
    assert key == "postgres"
    assert port == 5432


def test_detect_db_type_mssql(service):
    config = {"host": "server\\instance", "type": "mssql"}
    driver, is_mssql, key, params, port = service._detect_db_type(config)
    assert driver == "mssql+pytds"
    assert is_mssql is True
    assert key == "mssql"
    assert port is None


@pytest.mark.asyncio
async def test_get_engine_cache_hit(service, mock_cache):
    # Setup
    assistant = MagicMock()
    assistant.id = uuid4()

    mock_connector = MagicMock()
    mock_connector.id = uuid4()
    mock_connector.connector_type = ConnectorType.SQL

    # Mock DB result for SQL connector lookup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_connector
    service.db.execute = AsyncMock(return_value=mock_result)

    # Mock Cache Hit
    mock_engine = MagicMock()
    mock_cache.get_engine.return_value = mock_engine

    # Execute
    engine = await service.get_engine(assistant)

    # Assert
    assert engine == mock_engine
    mock_cache.get_engine.assert_called_with(assistant.id, mock_connector.id)


@pytest.mark.asyncio
async def test_vanna_engine_wrapper_aquery_success(mock_settings):
    # Setup
    mock_vanna = MagicMock()
    mock_vanna.llm = MagicMock()

    # Mock LLM synthesis
    from llama_index.core.base.response.schema import Response

    mock_vanna.llm.complete.return_value = "Synthesized answer"

    import pandas as pd

    df = pd.DataFrame([{"id": 1, "name": "Item 1"}])
    mock_vanna.submit_question.return_value = {"sql": "SELECT * FROM items", "dataframe": df}

    config = {"host": "db"}
    wrapper = VannaQueryEngineWrapper(mock_vanna, config, mock_settings)

    # Execute
    response = await wrapper.aquery("test question")

    # Assert
    assert any(x in response.response for x in ["Synthesized answer", "I found the"])
    assert ":::table" in response.response  # Structured data appended
    assert response.metadata["sql"] == "SELECT * FROM items"
    assert len(response.metadata["sql_query_result"]) == 1


@pytest.mark.asyncio
async def test_vanna_engine_wrapper_aquery_no_results(mock_settings):
    # Setup
    mock_vanna = MagicMock()
    import pandas as pd

    df = pd.DataFrame()  # Empty
    mock_vanna.submit_question.return_value = {"sql": "SELECT * FROM items", "dataframe": df}

    wrapper = VannaQueryEngineWrapper(mock_vanna, {}, mock_settings)

    # Execute
    response = await wrapper.aquery("test question")

    # Assert
    assert "no results" in response.response.lower()
    assert response.metadata["sql_query_result"] == []
