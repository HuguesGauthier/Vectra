"""
Async-safe context variable for tracking the active vector tool name during retrieval.

Why ContextVar and not a shared attribute?
With LLMMultiSelector, RouterQueryEngine calls asyncio.gather() on N engines
simultaneously. A shared attribute would be overwritten by each concurrent
engine before any RETRIEVE event fires. ContextVar propagates into child
coroutines/tasks but is NOT shared across sibling tasks, making it the
correct primitive for this pattern.

Usage:
- Set in IsolatedQueryEngine._aquery before calling the inner engine
- Read in StreamingCallbackHandler when a RETRIEVE event fires
"""

from contextvars import ContextVar
from typing import Optional

# Holds the tool name (e.g. "vector_search_gemini") for the currently
# executing retrieval coroutine. Reset automatically when the coroutine exits.
current_tool_name: ContextVar[Optional[str]] = ContextVar("current_tool_name", default=None)
