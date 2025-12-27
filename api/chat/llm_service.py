"""
LLM service with OpenAI integration, function calling, and model fallback.

Handles:
- Chat completions with streaming
- Function calling for tool execution
- Model fallback chain (GPT-4o -> GPT-4o-mini -> GPT-3.5-turbo)
- Token counting and cost tracking
"""
import json
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI, APIError, RateLimitError

from api.config import settings, should_use_cheap_model, get_model_cost
from api.models import ChatMessage, SessionContext, ChatResponse, ChatStreamChunk
from api.chat.prompts import build_system_prompt
from api.chat.tools import get_tool_definitions, execute_tool
from api.chat.token_counter import count_tokens, truncate_history, check_context_window
from api.chat.session_cache import get_session, set_session
from api.rag.retriever import retrieve_documents


# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def chat_completion(
    messages: List[ChatMessage],
    session_id: Optional[str] = None,
    context: Optional[SessionContext] = None,
    stream: bool = False,
    mode: str = "general"
) -> ChatResponse | AsyncGenerator[ChatStreamChunk, None]:
    """Process chat request with full RAG + function calling pipeline.

    Args:
        messages: Conversation history
        session_id: Session identifier for caching
        context: Session context (or retrieved from cache)
        stream: Whether to stream response
        mode: Conversation mode (general, navigation, interpretation, technical)

    Returns:
        ChatResponse or async generator of ChatStreamChunk
    """
    # 1. Get or create session context
    if not context and session_id:
        context = get_session(session_id)

    # 2. Retrieve relevant documents
    last_message = messages[-1].content if messages else ""
    rag_docs = await retrieve_documents(last_message, context)

    # 3. Build system prompt with context
    system_prompt = build_system_prompt(
        context=context,
        rag_documents=rag_docs,
        mode=mode
    )

    # 4. Check token budget and truncate if needed
    window_check = check_context_window(
        messages=messages,
        context=context,
        rag_documents=[d.get("text", "") for d in rag_docs],
        system_prompt=system_prompt
    )

    if not window_check["fits_in_window"]:
        messages = truncate_history(messages, max_tokens=80000)

    # 5. Determine model (cheap for simple queries)
    model = _select_model(messages, context)

    # 6. Prepare OpenAI messages
    openai_messages = _prepare_messages(system_prompt, messages)

    # 7. Get tool definitions
    tools = get_tool_definitions()

    if stream:
        return _stream_response(
            openai_messages, tools, model, context, session_id
        )
    else:
        return await _complete_response(
            openai_messages, tools, model, context, session_id
        )


def _select_model(
    messages: List[ChatMessage],
    context: Optional[SessionContext]
) -> str:
    """Select appropriate model based on query complexity.

    Args:
        messages: Conversation messages
        context: Session context

    Returns:
        Model name to use
    """
    if not messages:
        return settings.primary_model

    last_message = messages[-1].content.lower()

    # Use cheap model for simple queries
    if should_use_cheap_model(last_message, context):
        return settings.fallback_model  # GPT-4o-mini

    return settings.primary_model


def _prepare_messages(
    system_prompt: str,
    messages: List[ChatMessage]
) -> List[Dict[str, str]]:
    """Prepare messages for OpenAI API.

    Args:
        system_prompt: System prompt
        messages: User/assistant messages

    Returns:
        List of message dicts for OpenAI
    """
    openai_messages = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        openai_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    return openai_messages


async def _complete_response(
    messages: List[Dict[str, str]],
    tools: List[Dict],
    model: str,
    context: Optional[SessionContext],
    session_id: Optional[str]
) -> ChatResponse:
    """Get complete (non-streaming) response with function calling.

    Args:
        messages: OpenAI-formatted messages
        tools: Tool definitions
        model: Model to use
        context: Session context
        session_id: Session ID

    Returns:
        Complete ChatResponse
    """
    response_id = str(uuid.uuid4())[:8]
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        # Initial completion
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=2000
        )

        total_input_tokens += response.usage.prompt_tokens
        total_output_tokens += response.usage.completion_tokens

        # Handle function calls
        message = response.choices[0].message

        while message.tool_calls:
            # Execute tool calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # Execute tool
                result = await execute_tool(tool_name, tool_args, context)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            # Continue conversation with tool results
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000
            )

            total_input_tokens += response.usage.prompt_tokens
            total_output_tokens += response.usage.completion_tokens
            message = response.choices[0].message

        # Calculate cost
        cost = get_model_cost(model, total_input_tokens, total_output_tokens)

        # Update session cache
        if session_id and context:
            set_session(session_id, context)

        return ChatResponse(
            message=message.content or "",
            response_id=response_id,
            model=model,
            usage={
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "cost_usd": cost
            }
        )

    except RateLimitError:
        # Fallback to next model
        return await _fallback_completion(messages, tools, model, context, session_id)

    except APIError as e:
        return ChatResponse(
            message=f"API error: {str(e)}. Please try again.",
            response_id=response_id,
            model=model,
            usage={}
        )


async def _fallback_completion(
    messages: List[Dict[str, str]],
    tools: List[Dict],
    failed_model: str,
    context: Optional[SessionContext],
    session_id: Optional[str]
) -> ChatResponse:
    """Try fallback models when primary fails.

    Args:
        messages: OpenAI-formatted messages
        tools: Tool definitions
        failed_model: Model that failed
        context: Session context
        session_id: Session ID

    Returns:
        ChatResponse from fallback model
    """
    # Build fallback chain from settings
    fallback_chain = [
        settings.primary_model,
        settings.fallback_model,
        settings.emergency_model
    ]

    # Find next model in chain
    try:
        current_idx = fallback_chain.index(failed_model)
        next_models = fallback_chain[current_idx + 1:]
    except ValueError:
        next_models = fallback_chain[1:]  # Start from second model

    for model in next_models:
        try:
            return await _complete_response(
                messages, tools, model, context, session_id
            )
        except (RateLimitError, APIError):
            continue

    # All models failed
    return ChatResponse(
        message="All models are currently unavailable. Please try again later.",
        response_id=str(uuid.uuid4())[:8],
        model="none",
        usage={}
    )


async def _stream_response(
    messages: List[Dict[str, str]],
    tools: List[Dict],
    model: str,
    context: Optional[SessionContext],
    session_id: Optional[str]
) -> AsyncGenerator[ChatStreamChunk, None]:
    """Stream response chunks with function calling.

    Args:
        messages: OpenAI-formatted messages
        tools: Tool definitions
        model: Model to use
        context: Session context
        session_id: Session ID

    Yields:
        ChatStreamChunk objects
    """
    response_id = str(uuid.uuid4())[:8]

    try:
        # Initial streaming completion
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=2000,
            stream=True
        )

        collected_content = ""
        collected_tool_calls = []

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None

            if delta:
                # Stream content
                if delta.content:
                    collected_content += delta.content
                    yield ChatStreamChunk(
                        content=delta.content,
                        response_id=response_id,
                        done=False
                    )

                # Collect tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index >= len(collected_tool_calls):
                            collected_tool_calls.append({
                                "id": tc.id,
                                "name": tc.function.name if tc.function else "",
                                "arguments": tc.function.arguments if tc.function else ""
                            })
                        else:
                            if tc.function and tc.function.arguments:
                                collected_tool_calls[tc.index]["arguments"] += tc.function.arguments

        # Execute tool calls if any
        if collected_tool_calls:
            yield ChatStreamChunk(
                content="\n\n*Executing tools...*\n",
                response_id=response_id,
                done=False
            )

            for tool_call in collected_tool_calls:
                try:
                    tool_args = json.loads(tool_call["arguments"])
                    result = await execute_tool(
                        tool_call["name"], tool_args, context
                    )

                    # Add tool results to messages and continue
                    messages.append({
                        "role": "assistant",
                        "content": collected_content,
                        "tool_calls": [{
                            "id": tool_call["id"],
                            "type": "function",
                            "function": {
                                "name": tool_call["name"],
                                "arguments": tool_call["arguments"]
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result)
                    })

                except json.JSONDecodeError:
                    continue

            # Continue with tool results (non-streaming for simplicity)
            final_response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            final_content = final_response.choices[0].message.content or ""
            yield ChatStreamChunk(
                content="\n" + final_content,
                response_id=response_id,
                done=False
            )

        # Final chunk
        yield ChatStreamChunk(
            content="",
            response_id=response_id,
            done=True,
            model=model
        )

        # Update session cache
        if session_id and context:
            set_session(session_id, context)

    except Exception as e:
        yield ChatStreamChunk(
            content=f"\n\nError: {str(e)}",
            response_id=response_id,
            done=True,
            model=model
        )


async def simple_completion(
    prompt: str,
    model: str = "gpt-4o-mini"
) -> str:
    """Simple completion without tools or streaming.

    Args:
        prompt: User prompt
        model: Model to use

    Returns:
        Response text
    """
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content or ""
