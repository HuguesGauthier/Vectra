import logging
import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFound, FunctionalError, TechnicalError
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.assistant_service import AssistantService, get_assistant_service
from app.services.chat_service import ChatService, get_chat_service

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


async def get_optional_user(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> Optional[User]:
    """
    Resolves user from Bearer token if present, otherwise returns None.

    Does not raise 401 for invalid tokens, just returns None (for public access if allowed).

    Args:
        request: The FastAPI request object.
        db: The database session.

    Returns:
        The User object if found and valid, otherwise None.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        parts = auth_header.split(" ")
        if len(parts) != 2:
            return None
        token = parts[1]
        try:
            return await get_current_user(token=token, db=db)
        except Exception:
            return None
    return None


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
    user: Annotated[Optional[User], Depends(get_optional_user)],
) -> StreamingResponse:
    """
    Stream chat response for a session.

    Supports SSE (Server-Sent Events) via NDJSON or text/event-stream.

    Args:
        request: The chat request payload.
        chat_service: The chat service instance.
        assistant_service: The assistant service instance.
        user: The optional authenticated user.

    Returns:
        A StreamingResponse yielding the chat stream.

    Raises:
        EntityNotFound: If the assistant is not found.
        HTTPException: If authentication is required but user is not authenticated.
        TechnicalError: If an unexpected error occurs during initialization.
    """
    try:
        # 1. Fetch Assistant (raw SQLAlchemy model for ChatService)
        assistant_uuid = request.assistant_id
        assistant = await assistant_service.get_assistant_model(assistant_uuid)
        if not assistant:
            raise EntityNotFound("Assistant not found")

        # 2. Authorization Check
        user_id = str(user.id) if user else None
        if assistant.user_authentication and not user_id:
            logger.warning(f"Access denied for assistant {assistant.id}: User Authentication Required")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for this assistant",
            )

        # 3. Stream
        logger.info(f"Init Chat Stream | Session: {request.session_id} | User: {user_id}")

        # Standard RAG Stream (with Vanna routing via SQL connector type)
        return StreamingResponse(
            chat_service.stream_chat(
                request.message,
                assistant,
                request.session_id,
                language=request.language,
                history=request.history,
                user_id=user_id,
            ),
            media_type="application/x-ndjson",
        )

    except (FunctionalError, EntityNotFound, HTTPException):
        raise
    except Exception as e:
        logger.error(f"Chat stream initialization failed: {e}", exc_info=True)
        raise TechnicalError(f"Chat stream initialization failed: {e}")


@router.delete("/{session_id}")
async def reset_chat_session(
    session_id: str, chat_service: Annotated[ChatService, Depends(get_chat_service)]
) -> Dict[str, str]:
    """
    Resets the conversation history for a specific session ID.

    Args:
        session_id: The session ID to reset.
        chat_service: The chat service instance.

    Returns:
        A success message.

    Raises:
        TechnicalError: If resetting the conversation fails.
    """
    try:
        await chat_service.reset_conversation(session_id)
        return {"message": "Conversation history reset successfully"}
    except Exception as e:
        logger.error(f"Failed to reset conversation {session_id}: {e}", exc_info=True)
        if isinstance(e, (TechnicalError, FunctionalError)):
            raise
        raise TechnicalError(f"Failed to reset conversation: {e}")


@router.get("/{session_id}/history")
async def get_chat_history(
    session_id: str,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    user: Annotated[Optional[User], Depends(get_optional_user)],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieve conversation history for a specific session ID.

    Args:
        session_id: The session ID to retrieve history for.
        chat_service: The chat service instance.
        user: The optional authenticated user.

    Returns:
        A list of formatted chat messages.
    """
    try:
        # Get history from the chat repository (Postgres) instead of Redis for full persistence
        messages = await chat_service.chat_repository.get_messages(session_id)

        # Transform to frontend-compatible format
        formatted_messages = []
        for msg in messages:
            m = {
                "id": str(msg.id),  # Use actual message UUID
                "text": msg.content,
                "sender": "user" if msg.role == "user" else "bot",
            }
            # Include metadata (visualization, sources, etc.)
            if msg.metadata_:
                meta = msg.metadata_.copy()

                # Format Sources for Frontend (Source[] interface)
                if "sources" in meta and isinstance(meta["sources"], list):
                    meta["sources"] = [_format_source(s) for s in meta["sources"]]

                # Format Steps (Ensure labels are present)
                if "steps" in meta and isinstance(meta["steps"], list):
                    meta["steps"] = [_format_step(step) for step in meta["steps"]]
                    meta["steps"] = _rebuild_step_hierarchy(meta["steps"])

                # Format Visualization (Repair types if stringified by sanitization)
                if "visualization" in meta and meta["visualization"]:
                    meta["visualization"] = _format_visualization(meta["visualization"])

                m.update(meta)

            formatted_messages.append(m)

        return {"messages": formatted_messages}
    except Exception as e:
        logger.error(f"Failed to retrieve history for session {session_id}: {e}", exc_info=True)
        if isinstance(e, (TechnicalError, FunctionalError)):
            raise
        raise TechnicalError(f"Failed to retrieve history: {e}")


def _format_source(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats a single source for the frontend.

    Args:
        source: Raw source data.

    Returns:
        Formatted source data.
    """
    s_meta = source.get("metadata", {})
    file_name = s_meta.get("file_name") or s_meta.get("filename") or s_meta.get("name") or "Unknown"

    # Type detection (simplified)
    s_type = "txt"
    lower = file_name.lower()
    if lower.endswith(".pdf"):
        s_type = "pdf"
    elif lower.endswith(".docx"):
        s_type = "docx"

    return {
        "id": source.get("id"),
        "name": file_name,
        "type": s_type,
        "content": source.get("text"),
        "metadata": s_meta,
    }


def _format_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats a single step for the frontend.

    Args:
        step: Raw step data.

    Returns:
        Formatted step data.
    """
    # Filter out steps with no label and no meaningful data
    if not step.get("label"):
        # Let frontend handle missing labels via i18n
        pass

    # Map nesting metadata (backend 'is_substep' -> frontend 'isSubStep')
    step_meta = step.get("metadata", {})
    if step_meta.get("is_substep") or step_meta.get("isSubStep"):
        step["isSubStep"] = True

    return step


def _format_visualization(viz: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats visualization data for the frontend.

    Args:
        viz: Raw visualization data.

    Returns:
        Formatted visualization data.
    """
    # Ensure Series is a List
    if "series" in viz and isinstance(viz["series"], list):
        for s in viz["series"]:
            # Handle Treemap/Hierarchical Data (x, y dicts)
            if isinstance(s, dict) and "data" in s and isinstance(s["data"], list):
                for point in s["data"]:
                    if isinstance(point, dict) and "y" in point:
                        try:
                            # Force to float if it's a string
                            point["y"] = float(point["y"])
                        except (ValueError, TypeError):
                            point["y"] = 0.0
            # Handle standard Cartesian/Pie (simple value list)
            elif isinstance(s, (int, float, str)):
                pass

        # Fix for simple value lists (Pie/Donut) being stringified
        if viz.get("viz_type") in ["pie", "donut", "polarArea", "radialBar"]:
            try:
                viz["series"] = [float(x) for x in viz["series"]]
            except Exception:
                pass
    return viz


# 🔵 P1: Removed Debug/Test Endpoints (debug_stream, ping, test-db, test-assistant-service)
# Code Cleanliness and Security Hygiene.


def _rebuild_step_hierarchy(steps: list) -> list:
    """
    Reconstructs the parent->child tree structure from a flat list using parent_id.
    Returns only the root steps.
    """
    step_map = {s.get("step_id"): {**s, "sub_steps": []} for s in steps if s.get("step_id")}
    roots = []

    # Add steps without ID directly to roots so they are not lost
    for s in steps:
        if not s.get("step_id"):
            roots.append({**s, "sub_steps": []})

    for step in step_map.values():
        pid = step.get("parent_id")
        if pid and pid in step_map:
            step_map[pid]["sub_steps"].append(step)
        else:
            roots.append(step)

    # Sort each level by sequence
    for step in step_map.values():
        step["sub_steps"].sort(key=lambda x: x.get("sequence", 0))
    roots.sort(key=lambda x: x.get("sequence", 0))

    return roots
