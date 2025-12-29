"""
Building database query endpoints.

Provides REST API endpoints for querying the PostgreSQL building database.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from api.config.settings import settings
from api.db.connection import (
    run_query,
    run_query_with_count,
    get_building_schema,
    get_distinct_values,
    test_connection,
    get_table_stats
)
from .models import (
    BuildingFilter,
    BuildingQueryRequest,
    BuildingQueryResponse,
    BuildingSchemaResponse,
    BuildingStatsRequest,
    BuildingStatsResponse,
    DistinctValuesRequest,
    DistinctValuesResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/buildings", tags=["buildings"])

# Whitelisted columns for security (prevent SQL injection)
ALLOWED_COLUMNS = {
    "pand_id", "area", "height", "gem_bouwlagen", "residential_type",
    "bouwjaar", "postcode", "average_wwr", "perimeter", "volume",
    "footprint_area", "n_units", "label_energy_index",
    # New filterable columns
    "building_function", "building_type", "age_range", "non_residential_type",
    "woningtype", "gemeentenaam", "provincienaam", "wijknaam"
}

NUMERIC_COLUMNS = {
    "area", "height", "gem_bouwlagen", "bouwjaar", "average_wwr",
    "perimeter", "volume", "footprint_area", "n_units", "label_energy_index"
}

TEXT_COLUMNS = {
    "pand_id", "residential_type", "postcode", "building_function",
    "building_type", "age_range", "non_residential_type", "woningtype",
    "gemeentenaam", "provincienaam", "wijknaam"
}

# Columns available for distinct value queries (dropdown filters)
DISTINCT_VALUE_COLUMNS = {
    "residential_type", "building_function", "building_type",
    "age_range", "non_residential_type", "woningtype",
    "gemeentenaam", "provincienaam", "bouwjaar", "gem_bouwlagen"
}


def _build_where_clause(filters: List[BuildingFilter]) -> tuple[str, list]:
    """Build SQL WHERE clause from filters.

    Returns:
        Tuple of (where_clause_string, params_list)
    """
    if not filters:
        return "", []

    conditions = []
    params = []

    for f in filters:
        # Validate column name
        if f.column not in ALLOWED_COLUMNS:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{f.column}' is not allowed for filtering"
            )

        col = f.column

        if f.operator == "eq":
            conditions.append(f"{col} = %s")
            params.append(f.value)
        elif f.operator == "neq":
            conditions.append(f"{col} != %s")
            params.append(f.value)
        elif f.operator == "gt":
            conditions.append(f"{col} > %s")
            params.append(f.value)
        elif f.operator == "lt":
            conditions.append(f"{col} < %s")
            params.append(f.value)
        elif f.operator == "gte":
            conditions.append(f"{col} >= %s")
            params.append(f.value)
        elif f.operator == "lte":
            conditions.append(f"{col} <= %s")
            params.append(f.value)
        elif f.operator == "between":
            if not isinstance(f.value, list) or len(f.value) != 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"'between' operator requires [min, max] value"
                )
            conditions.append(f"{col} BETWEEN %s AND %s")
            params.extend(f.value)
        elif f.operator == "like":
            conditions.append(f"{col} LIKE %s")
            params.append(f"%{f.value}%")
        elif f.operator == "ilike":
            conditions.append(f"{col} ILIKE %s")
            params.append(f"%{f.value}%")
        elif f.operator == "in":
            if not isinstance(f.value, list):
                raise HTTPException(
                    status_code=400,
                    detail=f"'in' operator requires a list value"
                )
            placeholders = ", ".join(["%s"] * len(f.value))
            conditions.append(f"{col} IN ({placeholders})")
            params.extend(f.value)

    where_clause = " AND ".join(conditions)
    return f"WHERE {where_clause}" if where_clause else "", params


@router.get("/health")
async def buildings_health():
    """Check building database connection health."""
    is_connected = test_connection()
    return {
        "status": "ok" if is_connected else "error",
        "database_connected": is_connected,
        "host": settings.db_host,
        "port": settings.db_port,
        "database": settings.db_name
    }


@router.get("/debug/{pand_id}")
async def debug_pand_id(pand_id: str):
    """Debug endpoint to check pand_id lookup issues."""
    try:
        table = f"{settings.db_schema}.{settings.db_table}"
        pand_id_stripped = pand_id.lstrip('0') or '0'

        results = {}

        # Check exact string match
        query1 = f"SELECT pand_id, pg_typeof(pand_id) as dtype FROM {table} WHERE pand_id::text = %s LIMIT 1"
        try:
            r = run_query(query1, (pand_id,), fetch_all=False)
            results["exact_match"] = {"found": bool(r), "data": r[0] if r else None}
        except Exception as e:
            results["exact_match"] = {"error": str(e)}

        # Check stripped match
        query2 = f"SELECT pand_id, pg_typeof(pand_id) as dtype FROM {table} WHERE pand_id::text = %s LIMIT 1"
        try:
            r = run_query(query2, (pand_id_stripped,), fetch_all=False)
            results["stripped_match"] = {"found": bool(r), "data": r[0] if r else None}
        except Exception as e:
            results["stripped_match"] = {"error": str(e)}

        # Check if geometry column exists
        query3 = """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            AND column_name IN ('geometry', 'geom', 'centroid_lat', 'centroid_lon', 'lat', 'lon')
        """
        try:
            r = run_query(query3, (settings.db_schema, settings.db_table))
            results["geometry_columns"] = [row['column_name'] for row in r]
        except Exception as e:
            results["geometry_columns"] = {"error": str(e)}

        # Get sample pand_id from database
        query4 = f"SELECT pand_id, pg_typeof(pand_id) as dtype FROM {table} LIMIT 1"
        try:
            r = run_query(query4, fetch_all=False)
            results["sample_pand_id"] = r[0] if r else None
        except Exception as e:
            results["sample_pand_id"] = {"error": str(e)}

        return {
            "input_pand_id": pand_id,
            "stripped_pand_id": pand_id_stripped,
            "table": table,
            "results": results
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/schema", response_model=BuildingSchemaResponse)
async def get_schema():
    """Get the schema of the buildings table."""
    try:
        schema = get_building_schema()
        return BuildingSchemaResponse(
            columns=schema,
            filterable_columns=list(ALLOWED_COLUMNS),
            numeric_columns=list(NUMERIC_COLUMNS),
            text_columns=list(TEXT_COLUMNS)
        )
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=BuildingQueryResponse)
async def query_buildings(request: BuildingQueryRequest):
    """Query buildings with filters, sorting, and pagination."""
    start_time = time.time()

    try:
        # Build WHERE clause
        where_clause, params = _build_where_clause(request.filters)

        # Validate sort column
        sort_by = request.sort_by
        if sort_by and sort_by not in ALLOWED_COLUMNS:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{sort_by}' is not allowed for sorting"
            )

        # Determine columns to select
        if request.columns:
            # Validate requested columns
            for col in request.columns:
                if col not in ALLOWED_COLUMNS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{col}' is not allowed"
                    )
            select_cols = ", ".join(request.columns)
        else:
            # Default columns
            select_cols = "pand_id, area, height, gem_bouwlagen, residential_type, bouwjaar, postcode, average_wwr"

        table = f"{settings.db_schema}.{settings.db_table}"

        # Build queries
        order_clause = f"ORDER BY {sort_by} {request.sort_order}" if sort_by else "ORDER BY pand_id"

        query = f"""
            SELECT {select_cols}
            FROM {table}
            {where_clause}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        query_params = tuple(params + [request.limit, request.offset])

        count_query = f"""
            SELECT COUNT(*) as count
            FROM {table}
            {where_clause}
        """
        count_params = tuple(params) if params else None

        # Execute queries
        results, total_count = run_query_with_count(query, count_query, count_params, query_params)

        # Get actual column names from first result
        columns = list(results[0].keys()) if results else select_cols.split(", ")

        query_time = (time.time() - start_time) * 1000

        return BuildingQueryResponse(
            buildings=results,
            total_count=total_count,
            columns=columns,
            query_time_ms=round(query_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter-options")
async def get_filter_options():
    """Get all filter options for the building explorer UI.

    Returns distinct values for all categorical columns used in filters.
    This endpoint is optimized for populating dropdown menus.
    """
    try:
        table = f"{settings.db_schema}.{settings.db_table}"

        # Query all categorical options in a single database call
        query = f"""
            SELECT
                'building_function' as column_name,
                building_function as value,
                COUNT(*) as count
            FROM {table}
            WHERE building_function IS NOT NULL
            GROUP BY building_function

            UNION ALL

            SELECT
                'building_type' as column_name,
                building_type as value,
                COUNT(*) as count
            FROM {table}
            WHERE building_type IS NOT NULL AND building_type != ''
            GROUP BY building_type

            UNION ALL

            SELECT
                'residential_type' as column_name,
                residential_type as value,
                COUNT(*) as count
            FROM {table}
            WHERE residential_type IS NOT NULL AND residential_type != ''
            GROUP BY residential_type

            UNION ALL

            SELECT
                'non_residential_type' as column_name,
                non_residential_type as value,
                COUNT(*) as count
            FROM {table}
            WHERE non_residential_type IS NOT NULL AND non_residential_type != ''
            GROUP BY non_residential_type

            UNION ALL

            SELECT
                'age_range' as column_name,
                age_range as value,
                COUNT(*) as count
            FROM {table}
            WHERE age_range IS NOT NULL AND age_range != ''
            GROUP BY age_range

            ORDER BY column_name, count DESC
        """

        results = run_query(query)

        # Organize results by column
        options = {
            "building_function": [],
            "building_type": [],
            "residential_type": [],
            "non_residential_type": [],
            "age_range": []
        }

        for row in results:
            col = row['column_name']
            if col in options:
                options[col].append({
                    "value": row['value'],
                    "count": row['count']
                })

        # Sort age_range by logical order
        age_order = ['< 1945', '1945 - 1964', '1965 - 1974', '1975 - 1991',
                     '1992 - 2005', '2006 - 2014', '2015 and later']
        options['age_range'] = sorted(
            options['age_range'],
            key=lambda x: age_order.index(x['value']) if x['value'] in age_order else 999
        )

        return {
            "options": options,
            "columns": list(DISTINCT_VALUE_COLUMNS)
        }

    except Exception as e:
        logger.error(f"Failed to get filter options: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pand_id}")
async def get_building_by_id(pand_id: str):
    """Get a single building by its pand_id."""
    try:
        table = f"{settings.db_schema}.{settings.db_table}"
        query = f"SELECT * FROM {table} WHERE pand_id = %s"
        results = run_query(query, (pand_id,), fetch_all=False)

        if not results:
            raise HTTPException(status_code=404, detail=f"Building {pand_id} not found")

        return {"building": results[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get building {pand_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pand_id}/coordinates")
async def get_building_coordinates(pand_id: str):
    """Get the centroid coordinates of a building for camera navigation.

    Tries multiple approaches:
    1. PostGIS geometry centroid (if geometry column exists)
    2. Pre-computed centroid columns (centroid_lat, centroid_lon)
    3. Returns null coordinates if not available

    Note: Handles both string and numeric pand_id storage formats
    (leading zeros may be stripped if stored as bigint).
    """
    try:
        table = f"{settings.db_schema}.{settings.db_table}"

        # Handle pand_id that might be stored as bigint (stripping leading zeros)
        # Try both with and without leading zeros
        pand_id_stripped = pand_id.lstrip('0') or '0'

        # Try to get coordinates from PostGIS geometry first
        # Cast to text and try both formats (with and without leading zeros)
        query_geom = f"""
            SELECT
                pand_id,
                ST_Y(ST_Transform(ST_Centroid(geometry), 4326)) as lat,
                ST_X(ST_Transform(ST_Centroid(geometry), 4326)) as lon
            FROM {table}
            WHERE pand_id::text = %s OR pand_id::text = %s
            LIMIT 1
        """

        try:
            results = run_query(query_geom, (pand_id, pand_id_stripped), fetch_all=False)
            if results and results[0].get('lat') and results[0].get('lon'):
                return {
                    "pand_id": pand_id,
                    "lat": float(results[0]['lat']),
                    "lon": float(results[0]['lon']),
                    "source": "geometry"
                }
        except Exception as geom_err:
            logger.debug(f"Geometry query failed (column may not exist): {geom_err}")

        # Try pre-computed centroid/coordinate columns (multiple naming conventions)
        centroid_column_pairs = [
            ("lat", "lon"),
            ("centroid_lat", "centroid_lon"),
            ("latitude", "longitude"),
            ("y", "x"),
        ]

        for lat_col, lon_col in centroid_column_pairs:
            query_centroid = f"""
                SELECT pand_id, {lat_col} as lat, {lon_col} as lon
                FROM {table}
                WHERE pand_id::text = %s OR pand_id::text = %s
                LIMIT 1
            """
            try:
                results = run_query(query_centroid, (pand_id, pand_id_stripped), fetch_all=False)
                if results and results[0].get('lat') and results[0].get('lon'):
                    return {
                        "pand_id": pand_id,
                        "lat": float(results[0]['lat']),
                        "lon": float(results[0]['lon']),
                        "source": "centroid_columns"
                    }
            except Exception as centroid_err:
                logger.debug(f"Centroid columns ({lat_col}/{lon_col}) query failed: {centroid_err}")

        # Check if building exists at all (try both formats)
        query_exists = f"SELECT pand_id FROM {table} WHERE pand_id::text = %s OR pand_id::text = %s LIMIT 1"
        results = run_query(query_exists, (pand_id, pand_id_stripped), fetch_all=False)

        if not results:
            raise HTTPException(status_code=404, detail=f"Building {pand_id} not found")

        # Building exists but no coordinates available
        return {
            "pand_id": pand_id,
            "lat": None,
            "lon": None,
            "source": "unavailable",
            "message": "No geometry or centroid data available for this building"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get coordinates for {pand_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats", response_model=BuildingStatsResponse)
async def get_building_stats(request: BuildingStatsRequest):
    """Get statistics about buildings matching filters."""
    try:
        where_clause, params = _build_where_clause(request.filters)
        table = f"{settings.db_schema}.{settings.db_table}"

        # Main stats query
        stats_query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT pand_id) as unique_buildings,
                MIN(area) as area_min,
                MAX(area) as area_max,
                ROUND(AVG(area)::numeric, 1) as area_avg,
                MIN(height) as height_min,
                MAX(height) as height_max,
                ROUND(AVG(height)::numeric, 1) as height_avg,
                MIN(bouwjaar) as year_min,
                MAX(bouwjaar) as year_max,
                MIN(gem_bouwlagen) as floors_min,
                MAX(gem_bouwlagen) as floors_max,
                ROUND(AVG(gem_bouwlagen)::numeric, 1) as floors_avg
            FROM {table}
            {where_clause}
        """

        # Era breakdown query
        era_query = f"""
            SELECT
                CASE
                    WHEN bouwjaar < 1945 THEN 'Pre-1945'
                    WHEN bouwjaar < 1975 THEN '1945-1974'
                    WHEN bouwjaar < 1992 THEN '1975-1991'
                    WHEN bouwjaar < 2006 THEN '1992-2005'
                    ELSE '2006+'
                END as era,
                COUNT(*) as count,
                ROUND(AVG(area)::numeric, 1) as avg_area
            FROM {table}
            {where_clause}
            GROUP BY era
            ORDER BY era
        """

        # Type breakdown query
        type_query = f"""
            SELECT
                residential_type as type,
                COUNT(*) as count
            FROM {table}
            {where_clause}
            AND residential_type IS NOT NULL
            GROUP BY residential_type
            ORDER BY count DESC
            LIMIT 10
        """

        query_params = tuple(params) if params else None

        stats = run_query(stats_query, query_params)[0]
        era_results = run_query(era_query, query_params)
        type_results = run_query(type_query, query_params)

        return BuildingStatsResponse(
            total_count=stats['total_count'],
            unique_buildings=stats['unique_buildings'],
            area={
                "min": float(stats['area_min']) if stats['area_min'] else 0,
                "max": float(stats['area_max']) if stats['area_max'] else 0,
                "avg": float(stats['area_avg']) if stats['area_avg'] else 0
            },
            height={
                "min": float(stats['height_min']) if stats['height_min'] else 0,
                "max": float(stats['height_max']) if stats['height_max'] else 0,
                "avg": float(stats['height_avg']) if stats['height_avg'] else 0
            },
            year={
                "min": int(stats['year_min']) if stats['year_min'] else 0,
                "max": int(stats['year_max']) if stats['year_max'] else 0
            },
            floors={
                "min": float(stats['floors_min']) if stats['floors_min'] else 0,
                "max": float(stats['floors_max']) if stats['floors_max'] else 0,
                "avg": float(stats['floors_avg']) if stats['floors_avg'] else 0
            },
            by_era=era_results,
            by_type=type_results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/distinct", response_model=DistinctValuesResponse)
async def get_distinct_column_values(request: DistinctValuesRequest):
    """Get distinct values for a column (for dropdown filters)."""
    try:
        if request.column not in DISTINCT_VALUE_COLUMNS:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{request.column}' is not available for distinct values. Allowed: {DISTINCT_VALUE_COLUMNS}"
            )

        values = get_distinct_values(request.column, request.limit)
        return DistinctValuesResponse(
            column=request.column,
            values=values,
            count=len(values)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get distinct values: {e}")
        raise HTTPException(status_code=500, detail=str(e))
