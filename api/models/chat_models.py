"""
Pydantic models for chat API requests and responses.

Models:
- ChatMessage: Individual message in conversation
- SessionContext: Current session state (design vars, Pareto solutions, etc.)
- ChatRequest: Incoming chat request
- ChatResponse: Chat response with sources and metadata
- ChatStreamChunk: Streaming response chunk
- OptimizationJobStatus: Status of long-running optimization jobs
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "How do I start the retrofit optimization?"
            }
        }


class SessionContext(BaseModel):
    """Current session state from the frontend.

    Includes current stage, design variables, Pareto solutions, etc.
    This allows the chatbot to provide contextual responses.
    """

    session_id: Optional[str] = Field(
        None,
        description="Session ID for caching (auto-generated if not provided)"
    )
    current_stage: Optional[str] = Field(
        None,
        description="Current pipeline stage: 'inference', 'optimization', 'mcdm', etc."
    )
    building_id: Optional[str] = Field(
        None,
        description="Current building identifier"
    )
    design_variables: Optional[Dict[str, Any]] = Field(
        None,
        description="Current design variables (time_horizon, windows_U_Factor, etc.)"
    )
    pareto_solutions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Top 20 Pareto-optimal solutions (not all)"
    )
    selected_solution: Optional[str] = Field(
        None,
        description="ID of currently selected solution"
    )
    optimization_constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="Active optimization constraints"
    )
    mcdm_weights: Optional[Dict[str, float]] = Field(
        None,
        description="MCDM weights: energy, cost, co2, comfort"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "current_page": "optimization",
                "design_variables": {
                    "time_horizon": 2020,
                    "windows_U_Factor": 1.5,
                    "groundfloor_thermal_resistance": 2.5,
                    "ext_walls_thermal_resistance": 3.0,
                    "roof_thermal_resistance": 4.0
                },
                "pareto_solutions": [],
                "mcdm_weights": {
                    "energy": 0.3,
                    "cost": 0.2,
                    "co2": 0.3,
                    "comfort": 0.2
                }
            }
        }


class ChatRequest(BaseModel):
    """Request to the chat endpoint."""

    messages: List[ChatMessage] = Field(
        ...,
        description="Conversation history (last 10 messages recommended)"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for caching"
    )
    context: Optional[SessionContext] = Field(
        None,
        description="Current session state (optional)"
    )
    stream: bool = Field(
        False,
        description="Enable streaming responses via Server-Sent Events"
    )
    mode: Optional[str] = Field(
        "general",
        description="Conversation mode: general, navigation, interpretation, technical"
    )
    max_tokens: int = Field(
        1000,
        ge=100,
        le=4000,
        description="Maximum tokens in response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "Show me the cheapest 3 retrofit options"}
                ],
                "session_context": {
                    "current_page": "optimization",
                    "pareto_solutions": []
                },
                "stream": False,
                "max_tokens": 1000
            }
        }


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    message: str = Field(..., description="Assistant's response message")
    response_id: str = Field(..., description="Unique ID for feedback tracking")
    model: str = Field(default="gpt-4o", description="Model used for generation")
    usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Token usage and cost information"
    )
    sources: List[Dict[str, str]] = Field(
        default_factory=list,
        description="RAG sources used (thesis sections, case studies)"
    )
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="API calls made (inference, optimization, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": {
                    "role": "assistant",
                    "content": "Here are the 3 cheapest retrofit options..."
                },
                "sources": [
                    {
                        "text": "Window retrofits typically cost...",
                        "metadata": {"source": "methodology.md", "h1": "Cost Analysis"}
                    }
                ],
                "tool_calls": [
                    {"tool": "query_pareto_solutions", "result": {"count": 3}}
                ],
                "tokens_used": 1523,
                "response_id": "resp_abc123",
                "model_used": "gpt-4o",
                "cost_usd": 0.0152
            }
        }


class ChatStreamChunk(BaseModel):
    """Streaming response chunk for Server-Sent Events."""

    content: str = Field(..., description="Incremental text content")
    response_id: str = Field(..., description="Response ID for tracking")
    done: bool = Field(False, description="Whether streaming is complete")
    model: Optional[str] = Field(None, description="Model used (only in final chunk)")


class OptimizationJobStatus(BaseModel):
    """Status of a long-running optimization job.

    Used for async NSGA-II optimization which can take 30-60 seconds.
    """

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(
        ...,
        description="Job status: 'queued', 'running', 'completed', 'failed'"
    )
    progress: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Progress from 0.0 to 1.0"
    )
    result: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Pareto solutions (when status='completed')"
    )
    error: Optional[str] = Field(
        None,
        description="Error message (when status='failed')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "opt_abc123",
                "status": "running",
                "progress": 0.67,
                "result": None,
                "error": None
            }
        }
