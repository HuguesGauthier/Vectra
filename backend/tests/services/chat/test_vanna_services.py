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
    # Mock chat response
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
    # Fix: vanna_services.py accesses .client property directly
    service.client = client

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
    # Verify cleaning (regex check)
    # If the mock returning CREATE TABLE with COLLATE, it should be cleaned.
    # In our mock hit.payload = {"content": "CREATE TABLE users (id INT)"}, no COLLATE.


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
@patch("sqlalchemy.create_engine")
def test_run_sql(mock_create_engine, mock_settings, vanna_service):
    # Configure mock settings
    mock_settings.DB_HOST = "localhost"
    mock_settings.DB_USER = "sa"
    mock_settings.DB_PASSWORD = "password"
    mock_settings.DB_NAME = "testdb"

    # Mock engine and connection
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_create_engine.return_value = mock_engine
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    # Mock pandas read_sql
    with patch("pandas.read_sql") as mock_read_sql:
        mock_read_sql.return_value = pd.DataFrame({"id": [1]})

        # Override driver to be a real string to pass regex/replace checks
        vanna_service.config["driver"] = "ODBC Driver 17 for SQL Server"

        df = vanna_service.run_sql("SELECT 1")
        assert len(df) == 1
        # connection closed automatically by context manager (mocked via __exit__)
        mock_engine.connect.assert_called_once()


@patch("app.services.chat.vanna_services.settings")
def test_submit_question_happy_path(mock_settings, vanna_service, mock_llm):
    # Configure mock settings
    mock_settings.DB_HOST = "localhost"
    mock_settings.DB_USER = "sa"
    mock_settings.DB_PASSWORD = "password"
    mock_settings.DB_NAME = "testdb"

    # We don't need pandas or read_sql mock because run_sql is mocked

    # Mock LLM response string (JSON)
    json_response = '{"sql": "SELECT * FROM users", "explanation": "Fetching users"}'

    # Mock submit_prompt directly on instance
    vanna_service.submit_prompt = MagicMock(return_value=json_response)

    # Mock run_sql directly on instance to bypass DB/pandas
    vanna_service.run_sql = MagicMock(return_value=pd.DataFrame({"id": [1]}))

    result = vanna_service.submit_question("Show users")

    assert "sql" in result
    assert result["sql"] == "SELECT * FROM users"
    assert "dataframe" in result
    assert len(result["dataframe"]) == 1


def test_add_question_sql(vanna_service, mock_vector_service):
    point_id = vanna_service.add_question_sql("What is the total sales?", "SELECT SUM(Total) FROM sales")
    assert point_id != "error"
    assert point_id != "skipped"

    # Verify upsert was called
    mock_vector_service.client.upsert.assert_called_once()
    args, kwargs = mock_vector_service.client.upsert.call_args
    assert kwargs["collection_name"] == "test_collection"
    assert kwargs["points"][0].payload["type"] == "sql_training_pair"
    assert kwargs["points"][0].payload["sql"] == "SELECT SUM(Total) FROM sales"


def test_get_similar_question_sql(vanna_service, mock_vector_service):
    # Mock query_points to return a training pair
    training_hit = MagicMock()
    training_hit.payload = {"type": "sql_training_pair", "question": "past question", "sql": "SELECT * FROM past"}
    result = MagicMock()
    result.points = [training_hit]
    mock_vector_service.client.query_points.return_value = result

    examples = vanna_service.get_similar_question_sql("new question")
    assert len(examples) == 1
    assert examples[0]["question"] == "past question"
    assert examples[0]["sql"] == "SELECT * FROM past"


def test_system_instructions_mssql(vanna_service):
    vanna_service.config["type"] = "mssql"
    instructions = vanna_service._get_system_instructions()
    assert "RULES FOR SQL SERVER" in instructions
    assert "Full expressions are repeated" in instructions


def test_submit_question_auto_learn(vanna_service, mock_llm, mock_vector_service):
    # Mock successful SQL execution with data
    json_response = '{"sql": "SELECT * FROM sales", "explanation": "Fetching sales"}'
    vanna_service.submit_prompt = MagicMock(return_value=json_response)
    vanna_service.run_sql = MagicMock(return_value=pd.DataFrame({"Total": [100]}))

    # Enable auto-learn
    vanna_service.config["auto_learn"] = True

    # Spy on add_question_sql
    vanna_service.add_question_sql = MagicMock(wraps=vanna_service.add_question_sql)

    vanna_service.submit_question("Show sales")

    # Verify add_question_sql was called automatically
    vanna_service.add_question_sql.assert_called_once_with(question="Show sales", sql="SELECT * FROM sales")


def test_submit_question_retry_success(vanna_service, mock_llm):
    # 1. First response is an invalid SQL (uses alias in WHERE)
    bad_json = '{"sql": "SELECT DATEPART(yy, d) as Yr FROM t WHERE Yr=2024", "explanation": "Bad SQL"}'
    # 2. Second response (after error feedback) is a fixed SQL
    good_json = '{"sql": "SELECT DATEPART(yy, d) as Yr FROM t WHERE DATEPART(yy, d)=2024", "explanation": "Fixed SQL"}'

    # Mock submit_prompt to return bad then good
    vanna_service.submit_prompt = MagicMock(side_effect=[bad_json, good_json])

    # Mock run_sql to fail the first time then succeed
    def mock_run_sql(sql, **kwargs):
        if "WHERE Yr=2024" in sql:
            raise Exception("Invalid column name 'Yr'")
        return pd.DataFrame({"Yr": [2024]})

    vanna_service.run_sql = MagicMock(side_effect=mock_run_sql)
    vanna_service.config["type"] = "mssql"

    result = vanna_service.submit_question("Show year 2024")

    assert result["sql"] == "SELECT DATEPART(yy, d) as Yr FROM t WHERE DATEPART(yy, d)=2024"
    assert vanna_service.run_sql.call_count == 2
    assert vanna_service.submit_prompt.call_count == 2
    # Verify the correction prompt was sent
    args, _ = vanna_service.submit_prompt.call_args
    assert "Invalid column name 'Yr'" in args[0]
    assert "CRITICAL: SQL Server does NOT allow aliases" in args[0]
