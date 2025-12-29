"""
PostgreSQL database connection and query utilities.

Provides connection pooling and helper functions for querying
the building database.
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import logging

from api.config.settings import settings

logger = logging.getLogger(__name__)

# Connection pool (initialized lazily)
_connection_pool: Optional[pool.SimpleConnectionPool] = None


def _get_pool() -> pool.SimpleConnectionPool:
    """Get or create the connection pool."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=settings.db_host,
                port=settings.db_port,
                database=settings.db_name,
                user=settings.db_user,
                password=settings.db_password,
                connect_timeout=10
            )
            logger.info(f"Database pool created: {settings.db_host}:{settings.db_port}/{settings.db_name}")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    return _connection_pool


@contextmanager
def get_db_connection():
    """Context manager for getting a database connection from the pool."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def run_query(
    query: str,
    params: Optional[Tuple] = None,
    fetch_all: bool = True
) -> List[Dict[str, Any]]:
    """Run a query and return results as list of dictionaries.

    Args:
        query: SQL query string
        params: Optional tuple of parameters for the query
        fetch_all: If True, fetch all results. If False, fetch one.

    Returns:
        List of dictionaries with column names as keys
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if fetch_all:
                results = cursor.fetchall()
            else:
                result = cursor.fetchone()
                results = [result] if result else []
            return [dict(row) for row in results]


def run_query_with_count(
    query: str,
    count_query: str,
    count_params: Optional[Tuple] = None,
    query_params: Optional[Tuple] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Run a query and also get the total count.

    Args:
        query: SQL query string for fetching results
        count_query: SQL query string for counting total
        count_params: Optional tuple of parameters for count query
        query_params: Optional tuple of parameters for main query (if None, uses count_params)

    Returns:
        Tuple of (results list, total count)
    """
    # Use count_params for main query if query_params not provided
    if query_params is None:
        query_params = count_params

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get count first
            cursor.execute(count_query, count_params)
            count_result = cursor.fetchone()
            total_count = count_result['count'] if count_result else 0

            # Get results
            cursor.execute(query, query_params)
            results = cursor.fetchall()

            return [dict(row) for row in results], total_count


def get_building_schema() -> List[Dict[str, str]]:
    """Get the schema of the buildings table.

    Returns:
        List of dicts with column_name and data_type
    """
    query = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """
    return run_query(query, (settings.db_schema, settings.db_table))


def get_distinct_values(column: str, limit: int = 100) -> List[Any]:
    """Get distinct values for a column (useful for filters).

    Args:
        column: Column name
        limit: Maximum number of distinct values to return

    Returns:
        List of distinct values
    """
    # Whitelist of allowed columns for security
    allowed_columns = {
        'residential_type', 'postcode', 'bouwjaar', 'gem_bouwlagen',
        'building_function', 'building_type', 'age_range',
        'non_residential_type', 'woningtype', 'gemeentenaam', 'provincienaam'
    }

    if column not in allowed_columns:
        raise ValueError(f"Column '{column}' not allowed for distinct values")

    query = f"""
        SELECT DISTINCT {column}
        FROM {settings.db_schema}.{settings.db_table}
        WHERE {column} IS NOT NULL
        ORDER BY {column}
        LIMIT %s
    """
    results = run_query(query, (limit,))
    return [row[column] for row in results]


def test_connection() -> bool:
    """Test if database connection works."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def get_table_stats() -> Dict[str, Any]:
    """Get basic statistics about the buildings table."""
    query = f"""
        SELECT
            COUNT(*) as total_buildings,
            COUNT(DISTINCT pand_id) as unique_pand_ids,
            MIN(bouwjaar) as min_year,
            MAX(bouwjaar) as max_year,
            ROUND(AVG(area)::numeric, 1) as avg_area,
            ROUND(AVG(height)::numeric, 1) as avg_height,
            ROUND(AVG(gem_bouwlagen)::numeric, 1) as avg_floors
        FROM {settings.db_schema}.{settings.db_table}
    """
    results = run_query(query)
    return results[0] if results else {}
