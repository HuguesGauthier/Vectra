import sys
import os
import asyncio
from typing import Any, Dict, List, Optional
import time

# Add current directory to path
sys.path.append(os.getcwd())

from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.schema import QueryBundle, QueryType
from llama_index.core.query_engine import BaseQueryEngine, RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.callbacks import CallbackManager, CBEventType
from llama_index.core.callbacks.base import BaseCallbackHandler

# Import actual class from codebase
from app.factories.query_engine_factory import IsolatedQueryEngine


class TraceCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.events = []

    def on_event_start(self, event_type, payload=None, event_id="", parent_id="", **kwargs):
        print(f"[START] {event_type} (id={event_id}, parent={parent_id})")
        self.events.append(("start", event_type, event_id, parent_id))
        return event_id

    def on_event_end(self, event_type, payload=None, event_id="", **kwargs):
        print(f"[END]   {event_type} (id={event_id})")
        self.events.append(("end", event_type, event_id))

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        pass

    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict[str, Any]] = None) -> None:
        pass


from llama_index.core.base.response.schema import Response


class MockVectorEngine(BaseQueryEngine):
    def _query(self, query_bundle: QueryBundle) -> Response:
        with self.callback_manager.event(CBEventType.RETRIEVE, payload={"nodes": []}) as event:
            print("  -> Executing Mock Retrieval")
            time.sleep(0.1)
        return Response(response="mock result")

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def _get_prompt_modules(self) -> Dict[str, Any]:
        return {}


class MockSelector(LLMSingleSelector):
    def _select(self, choices: List[str], query_bundle: QueryBundle) -> Any:
        from llama_index.core.selectors.types import SelectorResult

        print("  -> Selecting Tool 0")
        return SelectorResult(selections=[{"index": 0, "reason": "test"}])

    async def _aselect(self, choices: List[str], query_bundle: QueryBundle) -> Any:
        return self._select(choices, query_bundle)


async def run_trace():
    handler = TraceCallbackHandler()
    cb_manager = CallbackManager([handler])

    # 1. Create Inner Engine
    inner_engine = MockVectorEngine(callback_manager=cb_manager)

    print("--- Calling Inner Engine directly ---")
    inner_engine.query("test")

    # 2. Create Wrapped Engine
    print("\n--- Calling Wrapped Engine ---")
    wrapped_engine = IsolatedQueryEngine(inner_engine)
    wrapped_engine.query("test")


if __name__ == "__main__":
    asyncio.run(run_trace())
