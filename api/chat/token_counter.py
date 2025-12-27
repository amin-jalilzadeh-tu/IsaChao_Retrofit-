"""
Token counting and management for OpenAI API calls.

Critical for:
- Preventing context window overflow (>128K tokens)
- Cost estimation before API calls
- Conversation history truncation
"""
import json
from typing import List
import tiktoken

from api.models import ChatMessage, SessionContext
from api.config import settings


def count_tokens(
    messages: List[ChatMessage],
    context: SessionContext | None = None,
    model: str = "gpt-4o"
) -> int:
    """Count tokens before API call to prevent overflow.

    Args:
        messages: List of conversation messages
        context: Optional session context
        model: Model name for tokenizer

    Returns:
        Total token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base for unknown models
        encoding = tiktoken.get_encoding("cl100k_base")

    total = 0

    # Count message tokens
    for msg in messages:
        # Add message formatting overhead (role + content structure)
        total += 4  # Message wrapper tokens
        total += len(encoding.encode(msg.content))

    # Count session context tokens
    if context:
        context_str = json.dumps(context.dict(exclude_none=True))
        total += len(encoding.encode(context_str))

    return total


def truncate_history(
    messages: List[ChatMessage],
    max_tokens: int = 100000,
    model: str = "gpt-4o"
) -> List[ChatMessage]:
    """Keep last N messages that fit within token budget.

    Always keeps the most recent message (current query).

    Args:
        messages: List of conversation messages
        max_tokens: Maximum tokens to allow
        model: Model name for tokenizer

    Returns:
        Truncated message list
    """
    if not messages:
        return []

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # Always keep last message (current query)
    result = [messages[-1]]
    total = len(encoding.encode(messages[-1].content)) + 4

    # Add earlier messages in reverse until budget exhausted
    for msg in reversed(messages[:-1]):
        msg_tokens = len(encoding.encode(msg.content)) + 4
        if total + msg_tokens > max_tokens:
            break
        result.insert(0, msg)
        total += msg_tokens

    return result


def estimate_cost(
    messages: List[ChatMessage],
    context: SessionContext | None = None,
    model: str = "gpt-4o",
    output_tokens: int = 500
) -> dict:
    """Estimate cost of API call.

    Args:
        messages: List of conversation messages
        context: Optional session context
        model: Model name
        output_tokens: Estimated output tokens

    Returns:
        Dictionary with token counts and cost
    """
    from api.config import get_model_cost

    input_tokens = count_tokens(messages, context, model)
    cost = get_model_cost(model, input_tokens, output_tokens)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost,
        "model": model
    }


def summarize_old_messages(
    messages: List[ChatMessage],
    keep_last_n: int = 5
) -> List[ChatMessage]:
    """Summarize older messages to compress conversation history.

    Keeps last N messages verbatim, summarizes older ones.

    Args:
        messages: List of conversation messages
        keep_last_n: Number of recent messages to keep

    Returns:
        List with summary + recent messages
    """
    if len(messages) <= keep_last_n:
        return messages

    # Recent messages to keep verbatim
    recent = messages[-keep_last_n:]

    # Old messages to summarize
    old = messages[:-keep_last_n]

    # Create summary
    summary_parts = []
    for msg in old:
        summary_parts.append(f"{msg.role}: {msg.content[:100]}...")

    summary_text = "Previous conversation summary:\n" + "\n".join(summary_parts)

    summary_message = ChatMessage(
        role="system",
        content=summary_text
    )

    return [summary_message] + recent


def check_context_window(
    messages: List[ChatMessage],
    context: SessionContext | None = None,
    rag_documents: List[str] | None = None,
    system_prompt: str = "",
    model: str = "gpt-4o",
    max_window: int = 128000
) -> dict:
    """Check if full context fits within model's window.

    Args:
        messages: List of conversation messages
        context: Optional session context
        rag_documents: Retrieved RAG documents
        system_prompt: System prompt text
        model: Model name
        max_window: Maximum context window size

    Returns:
        Dictionary with analysis
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # Count each component
    message_tokens = count_tokens(messages, context, model)
    system_tokens = len(encoding.encode(system_prompt)) if system_prompt else 0
    rag_tokens = sum(len(encoding.encode(doc)) for doc in (rag_documents or []))

    total = message_tokens + system_tokens + rag_tokens
    remaining = max_window - total

    return {
        "total_tokens": total,
        "message_tokens": message_tokens,
        "system_tokens": system_tokens,
        "rag_tokens": rag_tokens,
        "remaining_tokens": remaining,
        "fits_in_window": remaining > 2000,  # Reserve 2K for response
        "utilization_percent": (total / max_window) * 100
    }
