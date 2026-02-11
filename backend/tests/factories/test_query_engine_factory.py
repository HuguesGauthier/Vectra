import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.factories.query_engine_factory import UnifiedQueryEngineFactory
from app.schemas.enums import ConnectorType


@pytest.fixture
def mock_vector_service():
    service = AsyncMock()
    service.get_query_engine = AsyncMock()
    return service


@pytest.fixture
def mock_sql_service():
    sql_service = AsyncMock()
    sql_service.db = MagicMock()  # DB is usually not awaited directly
    sql_service.is_configured = AsyncMock()
    sql_service.get_engine = AsyncMock()
    return sql_service


@pytest.fixture
def factory(mock_vector_service, mock_sql_service):
    return UnifiedQueryEngineFactory(vector_service=mock_vector_service, sql_service=mock_sql_service)


@pytest.fixture
def mock_assistant():
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.linked_connectors = []
    assistant.model_provider = "gemini"
    assistant.instructions = "Be helpful."
    return assistant


@pytest.mark.asyncio
async def test_create_engine_docs_only(factory, mock_vector_service, mock_sql_service, mock_assistant):
    # Setup
    mock_sql_service.is_configured.return_value = False

    conn = MagicMock()
    conn.id = uuid4()
    conn.connector_type = ConnectorType.LOCAL_FOLDER
    mock_assistant.linked_connectors = [conn]

    with (
        patch("app.factories.query_engine_factory.SettingsService") as mock_settings_cls,
        patch(
            "app.factories.query_engine_factory.ChatEngineFactory.create_from_assistant", new_callable=AsyncMock
        ) as mock_chat_factory,
    ):

        mock_settings = mock_settings_cls.return_value
        mock_settings.load_cache = AsyncMock()

        # Execute
        await factory.create_engine(mock_assistant)

        # Verify
        mock_vector_service.get_query_engine.assert_called_once()
        assert mock_sql_service.get_engine.call_count == 0


@pytest.mark.asyncio
async def test_create_engine_sql_only(factory, mock_vector_service, mock_sql_service, mock_assistant):
    # Setup
    mock_sql_service.is_configured.return_value = True

    conn = MagicMock()
    conn.id = uuid4()
    conn.connector_type = ConnectorType.SQL
    mock_assistant.linked_connectors = [conn]

    # Execute
    await factory.create_engine(mock_assistant)

    # Verify
    mock_sql_service.get_engine.assert_called_once_with(mock_assistant)
    assert mock_vector_service.get_query_engine.call_count == 0


@pytest.mark.asyncio
async def test_create_engine_hybrid(factory, mock_vector_service, mock_sql_service, mock_assistant):
    # Setup
    mock_sql_service.is_configured.return_value = True

    conn_doc = MagicMock()
    conn_doc.id = uuid4()
    conn_doc.connector_type = ConnectorType.LOCAL_FOLDER

    conn_sql = MagicMock()
    conn_sql.id = uuid4()
    conn_sql.connector_type = ConnectorType.SQL

    mock_assistant.linked_connectors = [conn_doc, conn_sql]

    with (
        patch("app.factories.query_engine_factory.SettingsService") as mock_settings_cls,
        patch(
            "app.factories.query_engine_factory.ChatEngineFactory.create_from_assistant", new_callable=AsyncMock
        ) as mock_chat_factory,
        patch("app.factories.query_engine_factory.RouterQueryEngine") as mock_router_cls,
        patch("app.factories.query_engine_factory.LLMFactory.create_llm") as mock_llm_factory,
    ):

        mock_settings = mock_settings_cls.return_value
        mock_settings.load_cache = AsyncMock()
        mock_settings.get_value = AsyncMock(return_value="fake-model")

        # Execute
        await factory.create_engine(mock_assistant)

        # Verify
        mock_vector_service.get_query_engine.assert_called_once()
        mock_sql_service.get_engine.assert_called_once()
        mock_router_cls.assert_called_once()
