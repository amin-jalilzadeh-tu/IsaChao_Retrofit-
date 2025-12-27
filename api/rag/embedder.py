"""
OpenAI embedding generation for RAG.

Uses text-embedding-3-small model for cost-effective embeddings.
"""
from typing import List, Optional
import openai

from api.config import settings


# Lazy initialization of OpenAI client
_client: Optional[openai.OpenAI] = None


def _get_client() -> openai.OpenAI:
    """Get or create OpenAI client (lazy initialization)."""
    global _client
    if _client is None:
        _client = openai.OpenAI(
            api_key=settings.openai_api_key,
            organization=settings.openai_org_id
        )
    return _client


def get_embedding(text: str) -> List[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed

    Returns:
        1536-dimensional embedding vector
    """
    client = _get_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=text
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Generate embeddings for multiple texts.

    Batches requests to avoid rate limits.

    Args:
        texts: List of texts to embed
        batch_size: Number of texts per API call

    Returns:
        List of embedding vectors
    """
    client = _get_client()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def estimate_embedding_cost(num_texts: int, avg_tokens: int = 100) -> float:
    """Estimate cost for embedding generation.

    Args:
        num_texts: Number of texts to embed
        avg_tokens: Average tokens per text

    Returns:
        Estimated cost in USD
    """
    total_tokens = num_texts * avg_tokens
    # text-embedding-3-small: $0.02 per 1M tokens
    cost = (total_tokens / 1_000_000) * 0.02
    return cost
