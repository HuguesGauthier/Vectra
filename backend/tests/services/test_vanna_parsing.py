import pytest
from unittest.mock import MagicMock, patch
from app.services.chat.vanna_services import VectraCustomVanna, VannaBase


class TestVannaParsing:
    @pytest.fixture
    def vanna(self):
        # Patch VannaBase.__init__ since VectraCustomVanna calls super().__init__
        with (
            patch("app.services.chat.vanna_services.VannaBase.__init__", return_value=None),
            patch("app.services.chat.vanna_services.VectraCustomVanna.__init__", return_value=None),
        ):
            # We need to manually instantiate and set the method we are testing because __init__ is mocked
            vanna = VectraCustomVanna()
            # Restore the method we want to test if it was overriden or if instance is bare
            return vanna

    def test_extract_json_clean(self, vanna):
        text = '{"sql": "SELECT * FROM sales", "explanation": "test"}'
        result = vanna._extract_json_from_response(text)
        assert result.get("sql") == "SELECT * FROM sales"

    def test_extract_json_markdown(self, vanna):
        text = 'Here is the result:\n```json\n{"sql": "SELECT * FROM users", "explanation": "users"}\n```'
        result = vanna._extract_json_from_response(text)
        assert result.get("sql") == "SELECT * FROM users"

    def test_extract_json_messy(self, vanna):
        text = 'Sure! {"sql": "SELECT 1", "explanation": "one"} is the answer.'
        result = vanna._extract_json_from_response(text)
        assert result.get("sql") == "SELECT 1"

    def test_extract_json_fail(self, vanna):
        text = "Just some text"
        result = vanna._extract_json_from_response(text)
        assert result == {}
