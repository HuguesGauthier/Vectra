import sys
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd


# Mock problematic dependencies with a real class stub to allow inheritance
class VannaBaseStub:
    def __init__(self, config=None):
        self.config = config or {}

    def __getattr__(self, name):
        return MagicMock()


vanna_mock = MagicMock()
vanna_base_mock = MagicMock()
vanna_base_mock.VannaBase = VannaBaseStub

sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = vanna_mock
sys.modules["vanna.base"] = vanna_base_mock

import importlib
import app.services.chat.vanna_services

importlib.reload(app.services.chat.vanna_services)
from app.services.chat.vanna_services import VectraCustomVanna


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock chat response
    chat_response = MagicMock()
    chat_response.message.content = "SELECT * FROM users"
    llm.chat.return_value = chat_response

    # Mock complete response
    complete_response = MagicMock()
    complete_response.text = "SELECT * FROM users"
    llm.complete.return_value = complete_response
    return llm


@pytest.fixture
def mock_embedding():
    model = MagicMock()
    model.get_text_embedding.return_value = [0.1, 0.2, 0.3]
    return model


@pytest.fixture
def mock_vector_service():
    service = MagicMock()
    client = MagicMock()
    service.get_qdrant_client.return_value = client

    # Mock query_points result
    hit = MagicMock()
    hit.payload = {"content": "CREATE TABLE users (id INT)"}
    # Important: result must have 'points' attribute that is a LIST
    result = MagicMock()
    result.points = [hit]
    client.query_points.return_value = result

    # Also mock it as an iterable just in case
    client.query_points.return_value.__iter__.return_value = [hit]

    return service


@pytest.fixture
def vanna_service(mock_llm, mock_embedding, mock_vector_service):
    return VectraCustomVanna(
        config={"type": "postgres"},
        llm=mock_llm,
        embedding_service=mock_embedding,
        vector_service=mock_vector_service,
        connector_id="conn_123",
        collection_name="test_collection",
    )


def test_get_related_ddl(vanna_service):
    ddl = vanna_service.get_related_ddl("How many users?")
    assert len(ddl) == 1
    assert "CREATE TABLE users" in ddl[0]


def test_submit_prompt_string(vanna_service, mock_llm):
    response = vanna_service.submit_prompt("Generate SQL for users")
    assert response == "SELECT * FROM users"
    mock_llm.chat.assert_called_once()


def test_submit_prompt_list(vanna_service, mock_llm):
    history = [{"role": "user", "content": "list users"}]
    response = vanna_service.submit_prompt(history)
    assert response == "SELECT * FROM users"
    # Verify first message is system prompt
    args, _ = mock_llm.chat.call_args
    messages = args[0]
    assert messages[0].role == "system"
    assert messages[1].role == "user"


@patch("app.services.chat.vanna_services.settings")
@patch("pyodbc.connect")
def test_run_sql(mock_connect, mock_settings, vanna_service):
    # Configure mock settings
    mock_settings.DB_HOST = "localhost"
    mock_settings.DB_USER = "sa"
    mock_settings.DB_PASSWORD = "password"
    mock_settings.DB_NAME = "testdb"

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    # Mock pandas read_sql
    with patch("pandas.read_sql") as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame({"id": [1]})
        df = vanna_service.run_sql("SELECT 1")
        assert len(df) == 1
        mock_conn.close.assert_called_once()


@patch("pandas.read_sql")
def test_submit_question_happy_path(mock_read_sql, vanna_service, mock_llm):
    # Mock pandas read_sql to return a dummy df
    mock_read_sql.return_value = pd.DataFrame({"id": [1]})

    result = vanna_service.submit_question("Show users")
    assert "sql" in result
    assert "dataframe" in result
    assert result["sql"] == "SELECT * FROM users"
