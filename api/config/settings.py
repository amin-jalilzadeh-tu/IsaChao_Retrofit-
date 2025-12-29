"""
Centralized settings and configuration for the Isabella2 chatbot.

Handles:
- Environment variable loading
- OpenAI API configuration
- Model fallback chain (GPT-4o → GPT-4o-mini → GPT-3.5-turbo)
- Cost tracking per model
- RAG and conversation parameters
"""
import os
from typing import Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI API Configuration (optional for building database features)
    openai_api_key: str | None = None
    openai_org_id: str | None = None

    # ChromaDB Configuration
    chromadb_path: str = "./chroma_db"

    # Embedding Model
    embedding_model: str = "text-embedding-3-small"

    # LLM Configuration
    llm_model: str = "gpt-4o"  # Primary model
    primary_model: str = "gpt-4o"
    fallback_model: str = "gpt-4o-mini"
    emergency_model: str = "gpt-3.5-turbo"

    # Conversation Settings
    max_conversation_history: int = 10
    max_rag_documents: int = 5
    default_temperature: float = 0.3

    # Token Management
    max_tokens_per_request: int = 120000  # Reserve 8K for response
    default_max_output_tokens: int = 2000

    # Model Pricing (per 1M tokens)
    model_pricing: Dict[str, Dict[str, float]] = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }

    # Session Cache
    session_cache_ttl: int = 3600  # 1 hour
    session_cache_maxsize: int = 1000

    # PostgreSQL Building Database
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "research"
    db_user: str = "aminj"
    db_password: str = ""  # Set via DB_PASSWORD env var
    db_schema: str = "amin"
    db_table: str = "buildings_1_deducted"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow case-insensitive env var names
        case_sensitive = False
        # Ignore extra environment variables
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model invocation.

    Args:
        model: Model name (e.g., "gpt-4o")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    if model not in settings.model_pricing:
        # Default to most expensive model for safety
        model = "gpt-4o"

    pricing = settings.model_pricing[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def should_use_cheap_model(query: str, context: any = None) -> bool:
    """Determine if query is simple enough for cheaper model.

    Simple queries (navigation, greetings) can use GPT-4o-mini
    to save ~80% on costs.

    Args:
        query: User query text
        context: Optional session context (for future use)

    Returns:
        True if GPT-4o-mini should be used
    """
    query_lower = query.lower()

    # Navigation queries
    navigation_keywords = [
        "how do i", "where", "what page", "next step",
        "how to", "what is", "explain", "help"
    ]

    # Greetings
    greetings = ["hello", "hi", "hey", "thanks", "thank you"]

    # Short queries (<50 chars) with navigation keywords
    if len(query) < 50 and any(kw in query_lower for kw in navigation_keywords):
        return True

    # Greetings
    if any(greeting in query_lower for greeting in greetings):
        return True

    return False
