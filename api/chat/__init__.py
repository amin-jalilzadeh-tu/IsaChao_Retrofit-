"""Chat module for Isabella2 chatbot.

Provides LLM-powered conversational interface for:
- Pipeline navigation guidance
- Optimization results interpretation
- Function calling for inference and optimization
"""
from api.chat.endpoints import router
from api.chat.llm_service import chat_completion, simple_completion
from api.chat.session_cache import get_session, set_session, delete_session
from api.chat.tools import execute_tool, get_tool_definitions

__all__ = [
    "router",
    "chat_completion",
    "simple_completion",
    "get_session",
    "set_session",
    "delete_session",
    "execute_tool",
    "get_tool_definitions",
]
