import pytest
import asyncio
from unittest.mock import MagicMock
from app.services.chat.callbacks import StreamingCallbackHandler
from app.services.chat.types import PipelineStepType
from llama_index.core.callbacks.schema import CBEventType


@pytest.mark.asyncio
class TestStreamingCallbackHandler:

    @pytest.fixture
    async def handler(self):
        return StreamingCallbackHandler(asyncio.Queue())

    async def test_extract_usage_openai_style(self, handler):
        """Test usage extraction from OpenAI-style payload."""
        payload = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        usage = handler._extract_usage_from_payload(payload)
        assert usage == {"input": 10, "output": 20}

    async def test_extract_usage_gemini_dict_style(self, handler):
        """Test usage extraction from Gemini-style (dict) response."""
        response = MagicMock()
        response.raw = {"usage_metadata": {"prompt_token_count": 5, "candidates_token_count": 15}}
        payload = {"response": response}
        usage = handler._extract_usage_from_payload(payload)
        assert usage == {"input": 5, "output": 15}

    async def test_extract_usage_gemini_object_style(self, handler):
        """Test usage extraction from Gemini-style (object) response."""
        usage_meta = MagicMock()
        usage_meta.prompt_token_count = 8
        usage_meta.candidates_token_count = 12

        response = MagicMock()
        response.raw = MagicMock()
        # Mocking usage_metadata as an object attribute
        response.raw.usage_metadata = usage_meta

        payload = {"response": response}
        usage = handler._extract_usage_from_payload(payload)
        assert usage == {"input": 8, "output": 12}

    async def test_determine_step_type_sql(self, handler):
        """Test detection of SQL generation step."""
        # Using the helper directly or via on_event_start
        payload = {"serialized": "NLSQLRetriever"}
        step_type = handler._determine_step_type(CBEventType.LLM, payload)

        assert step_type == PipelineStepType.SQL_GENERATION
        assert handler._is_sql_flow is True

    async def test_determine_step_type_router(self, handler):
        """Test detection of Router selection step."""
        payload = {"serialized": "LLMSingleSelector"}
        step_type = handler._determine_step_type(CBEventType.LLM, payload)

        assert step_type == PipelineStepType.ROUTER_SELECTION

    async def test_determine_step_type_tool(self, handler):
        """Test detection of Tool execution."""
        step_type = handler._determine_step_type(CBEventType.FUNCTION_CALL, {})
        assert step_type == PipelineStepType.TOOL_EXECUTION
        assert handler._has_used_tools is True

    async def test_determine_step_type_synthesis(self, handler):
        """Test detection of LLM after Tool (ROUTER_REASONING).

        Note: ROUTER_SYNTHESIS is no longer emitted by the callback handler.
        It is a dedicated step in AgenticProcessor that wraps the actual
        streaming content generation (where real duration/tokens are available).
        Post-tool LLM callbacks are classified as ROUTER_REASONING.
        """
        handler._has_used_tools = True
        step_type = handler._determine_step_type(CBEventType.LLM, {})
        assert step_type == PipelineStepType.ROUTER_REASONING

    async def test_enrich_retrieval_payload(self, handler):
        """Test retrieval payload enrichment."""
        # Case 1: Standard retrieval
        payload = {"nodes": [1, 2, 3]}
        out = {}
        handler._enrich_retrieval_payload(payload, out)
        assert out["source_count"] == 3
        assert "is_sql" not in out

        # Case 2: SQL Flow active
        handler._is_sql_flow = True
        out = {}
        handler._enrich_retrieval_payload(payload, out)
        assert out["is_sql"] is True

    async def test_obs_event_full_queue(self):
        """Test graceful handling of full queue."""
        q = asyncio.Queue(maxsize=1)
        handler = StreamingCallbackHandler(q)

        # Fill queue
        await q.put("dummy")

        # Trigger event (should not raise)
        handler.on_event_start(CBEventType.RETRIEVE, {"nodes": []}, "evt1")

        # Verify queue is still full but didn't crash
        assert q.full()
