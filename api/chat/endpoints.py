"""
FastAPI endpoints for chat functionality.

Provides:
- POST /api/chat - Main chat endpoint with streaming support
- POST /api/chat/feedback - User feedback collection
- GET /api/chat/session/{session_id} - Get session state
- DELETE /api/chat/session/{session_id} - Clear session
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from api.models import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    SessionContext
)
from api.chat.llm_service import chat_completion
from api.chat.session_cache import (
    get_session,
    set_session,
    delete_session,
    get_cache_stats
)
from api.chat.prompts import get_conversation_starter


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process chat request.

    Handles conversation with RAG retrieval and function calling.
    Supports both streaming and non-streaming responses.

    Args:
        request: ChatRequest with messages, session_id, and options

    Returns:
        ChatResponse with assistant message and usage stats
    """
    # Validate request
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")

    # Get or create context
    context = None
    if request.session_id:
        context = get_session(request.session_id)

    if request.context:
        # Merge provided context with cached
        if context:
            # Update cached context with new values
            context_dict = context.dict()
            context_dict.update(request.context.dict(exclude_none=True))
            context = SessionContext(**context_dict)
        else:
            context = request.context

    # Process chat
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            _stream_chat(request.messages, request.session_id, context),
            media_type="text/event-stream"
        )
    else:
        # Return complete response
        response = await chat_completion(
            messages=request.messages,
            session_id=request.session_id,
            context=context,
            stream=False,
            mode=request.mode or "general"
        )

        # Update session
        if request.session_id and context:
            set_session(request.session_id, context)

        return response


async def _stream_chat(
    messages: list[ChatMessage],
    session_id: Optional[str],
    context: Optional[SessionContext]
):
    """Stream chat response as Server-Sent Events.

    Args:
        messages: Conversation messages
        session_id: Session identifier
        context: Session context

    Yields:
        SSE-formatted chunks
    """
    generator = await chat_completion(
        messages=messages,
        session_id=session_id,
        context=context,
        stream=True
    )

    async for chunk in generator:
        data = {
            "content": chunk.content,
            "response_id": chunk.response_id,
            "done": chunk.done
        }
        if chunk.done and chunk.model:
            data["model"] = chunk.model

        yield f"data: {json.dumps(data)}\n\n"


@router.post("/feedback")
async def submit_feedback(
    response_id: str,
    rating: int,
    comment: Optional[str] = None
) -> dict:
    """Submit feedback for a response.

    Args:
        response_id: ID of the response to rate
        rating: 1-5 star rating
        comment: Optional text feedback

    Returns:
        Confirmation message
    """
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    # TODO: Store feedback in database
    # For now, just log it
    print(f"Feedback received: response_id={response_id}, rating={rating}, comment={comment}")

    return {
        "status": "success",
        "message": "Thank you for your feedback!"
    }


@router.get("/session/{session_id}")
async def get_session_state(session_id: str) -> dict:
    """Get current session state.

    Args:
        session_id: Session identifier

    Returns:
        Session context or empty state
    """
    context = get_session(session_id)

    if context:
        return {
            "session_id": session_id,
            "context": context.dict(),
            "has_pareto_solutions": bool(context.pareto_solutions),
            "current_stage": context.current_stage
        }
    else:
        return {
            "session_id": session_id,
            "context": None,
            "message": "Session not found or expired"
        }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str) -> dict:
    """Clear session data.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    delete_session(session_id)
    return {
        "status": "success",
        "message": f"Session {session_id} cleared"
    }


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Service status and cache stats
    """
    cache_stats = get_cache_stats()

    return {
        "status": "healthy",
        "service": "isabella2-chat",
        "cache": cache_stats
    }


@router.post("/session/{session_id}/context")
async def update_session_context(
    session_id: str,
    context: SessionContext
) -> dict:
    """Update session context with new data.

    Use this to:
    - Set Pareto solutions after optimization
    - Update current pipeline stage
    - Store design variables

    Args:
        session_id: Session identifier
        context: New context data to merge

    Returns:
        Updated session state
    """
    existing = get_session(session_id)

    if existing:
        # Merge contexts
        existing_dict = existing.dict()
        new_dict = context.dict(exclude_none=True)
        existing_dict.update(new_dict)
        merged = SessionContext(**existing_dict)
    else:
        merged = context

    set_session(session_id, merged)

    return {
        "status": "success",
        "session_id": session_id,
        "context": merged.dict()
    }


@router.get("/start")
async def get_starter(session_id: Optional[str] = None) -> dict:
    """Get conversation starter based on session state.

    Args:
        session_id: Optional session identifier

    Returns:
        Appropriate greeting message
    """
    context = None
    if session_id:
        context = get_session(session_id)

    starter = get_conversation_starter(context)

    return {
        "message": starter,
        "has_context": context is not None
    }
