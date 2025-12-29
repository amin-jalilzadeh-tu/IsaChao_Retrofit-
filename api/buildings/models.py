"""
Pydantic models for building database queries.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union, Literal


class BuildingFilter(BaseModel):
    """A single filter condition for building queries."""
    column: str = Field(..., description="Column name to filter on")
    operator: Literal["eq", "neq", "gt", "lt", "gte", "lte", "between", "like", "ilike", "in"] = Field(
        ..., description="Comparison operator"
    )
    value: Union[str, float, int, List[Union[str, float, int]], None] = Field(
        ..., description="Value to compare against. For 'between', use [min, max]. For 'in', use list of values."
    )


class BuildingQueryRequest(BaseModel):
    """Request model for querying buildings."""
    filters: List[BuildingFilter] = Field(default_factory=list, description="List of filter conditions")
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    sort_order: Literal["asc", "desc"] = Field("asc", description="Sort order")
    limit: int = Field(50, ge=1, le=500, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    columns: Optional[List[str]] = Field(None, description="Specific columns to return (None = all)")


class BuildingQueryResponse(BaseModel):
    """Response model for building queries."""
    buildings: List[Dict[str, Any]] = Field(..., description="List of building records")
    total_count: int = Field(..., description="Total count matching filters (before limit)")
    columns: List[str] = Field(..., description="Column names in the response")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")


class BuildingSchemaResponse(BaseModel):
    """Response model for building table schema."""
    columns: List[Dict[str, str]] = Field(..., description="List of column definitions")
    filterable_columns: List[str] = Field(..., description="Columns available for filtering")
    numeric_columns: List[str] = Field(..., description="Numeric columns (for range filters)")
    text_columns: List[str] = Field(..., description="Text columns (for text search)")


class BuildingStatsRequest(BaseModel):
    """Request model for building statistics."""
    filters: List[BuildingFilter] = Field(default_factory=list, description="Filters to apply before computing stats")


class BuildingStatsResponse(BaseModel):
    """Response model for building statistics."""
    total_count: int
    unique_buildings: int
    area: Dict[str, float] = Field(..., description="Area stats: min, max, avg")
    height: Dict[str, float] = Field(..., description="Height stats: min, max, avg")
    year: Dict[str, int] = Field(..., description="Year stats: min, max")
    floors: Dict[str, float] = Field(..., description="Floor stats: min, max, avg")
    by_era: List[Dict[str, Any]] = Field(..., description="Breakdown by construction era")
    by_type: List[Dict[str, Any]] = Field(..., description="Breakdown by residential type")


class DistinctValuesRequest(BaseModel):
    """Request for distinct values of a column."""
    column: str = Field(..., description="Column to get distinct values for")
    limit: int = Field(100, ge=1, le=500, description="Maximum values to return")


class DistinctValuesResponse(BaseModel):
    """Response with distinct values."""
    column: str
    values: List[Any]
    count: int
