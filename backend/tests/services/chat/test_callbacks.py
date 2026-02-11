import pytest
import asyncio
from unittest.mock import MagicMock
from app.services.chat.callbacks import StreamingCallbackHandler
from app.services.chat.types import PipelineStepType
from llama_index.core.callbacks.schema import CBEventType

class TestStreamingCallbackHandler:
    
    @pytest.fixture
    def handler(self):
        return StreamingCallbackHandler(asyncio.Queue())

    def test_extract_usage_openai_style(self, handler):
        """Test usage extraction from OpenAI-style payload."""
        payload = {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20
            }
        }
        usage = handler._extract_usage_from_payload(payload)
        assert usage == {"input": 10, "output": 20}

    def test_extract_usage_gemini_dict_style(self, handler):
        """Test usage extraction from Gemini-style (dict) response."""
        response = MagicMock()
        response.raw = {
            "usage_metadata": {
                "prompt_token_count": 5,
                "candidates_token_count": 15
            }
        }
        payload = {"response": response}
        usage = handler._extract_usage_from_payload(payload)
        assert usage == {"input": 5, "output": 15}

    def test_extract_usage_gemini_object_style(self, handler):
        """Test usage extraction from Gemini-style (object) response."""
        usage_meta = MagicMock()
        usage_meta.prompt_token_count = 8
        usage_meta.candidates_token_count = 12
        
        response = MagicMock()
        response.raw = MagicMock()
        response.raw.usage_metadata = usage_meta
        
        payload = {"response": response}
        usage = handler._extract_usage_from_payload(payload)
        assert usage == {"input": 8, "output": 12}

    def test_obs_event_sql_detection(self, handler):
        """Test detection of SQL generation step."""
        # Start event
        payload = {
            "serialized": "NLSQLRetriever"
        }
        handler.on_event_start(
            event_type=CBEventType.LLM,
            payload=payload,
            event_id="evt1"
        )
        
        assert "evt1" in handler._event_map
        assert handler._event_map["evt1"]["step_type"] == PipelineStepType.SQL_GENERATION
        assert handler._is_sql_flow is True

    def test_obs_event_router_selection(self, handler):
        """Test detection of Router selection step."""
        # Start event with Selector in serialized
        payload = {
            "serialized": "LLMSingleSelector"
        }
        handler.on_event_start(
            event_type=CBEventType.LLM,
            payload=payload,
            event_id="evt2"
        )
        
        assert "evt2" in handler._event_map
        assert handler._event_map["evt2"]["step_type"] == PipelineStepType.ROUTER_SELECTION
