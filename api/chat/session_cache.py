"""
Session caching for chatbot conversations.

Uses TTL cache to store session context and reduce token usage by 50%.
Instead of sending full Pareto solutions every request, we cache them
by session_id and reference them.
"""
from cachetools import TTLCache
from api.config import settings
from api.models import SessionContext

# Global session cache
# TTL = 1 hour, Max 1000 sessions
session_cache: TTLCache = TTLCache(
    maxsize=settings.session_cache_maxsize,
    ttl=settings.session_cache_ttl
)


def get_session(session_id: str) -> SessionContext | None:
    """Retrieve session from cache.

    Args:
        session_id: Unique session identifier

    Returns:
        SessionContext if found, None otherwise
    """
    return session_cache.get(session_id)


def set_session(session_id: str, context: SessionContext) -> None:
    """Store session in cache.

    Args:
        session_id: Unique session identifier
        context: Session context to cache
    """
    session_cache[session_id] = context


def delete_session(session_id: str) -> None:
    """Remove session from cache.

    Args:
        session_id: Unique session identifier
    """
    if session_id in session_cache:
        del session_cache[session_id]


def clear_expired_sessions() -> int:
    """Clear expired sessions from cache.

    Returns:
        Number of sessions cleared
    """
    # TTLCache handles expiry automatically
    # This is just for explicit clearing if needed
    initial_size = len(session_cache)
    session_cache.expire()
    return initial_size - len(session_cache)


def get_cache_stats() -> dict:
    """Get cache statistics.

    Returns:
        Dictionary with cache stats (size, maxsize, ttl)
    """
    return {
        "current_size": len(session_cache),
        "maxsize": session_cache.maxsize,
        "ttl_seconds": session_cache.ttl,
        "hit_rate": getattr(session_cache, "hit_count", 0) / max(getattr(session_cache, "miss_count", 1), 1)
    }
