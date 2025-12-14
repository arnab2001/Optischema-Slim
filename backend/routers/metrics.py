"""
Metrics Router for OptiSchema Slim.
Exposes endpoints for fetching query metrics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from services.metric_service import metric_service

router = APIRouter(
    prefix="/api/metrics",
    tags=["metrics"]
)

@router.get("/")
async def get_metrics(
    sample_size: int = Query(default=50, ge=10, le=500, description="Number of queries to fetch"),
    include_system: bool = Query(default=False, description="Include system/control queries (COMMIT, ROLLBACK, etc.)")
):
    """
    Get query metrics from pg_stat_statements.
    Returns both sampled metrics and total count.
    """
    result = await metric_service.fetch_query_metrics(
        sample_size=sample_size,
        include_system_queries=include_system
    )
    return result

@router.get("/vitals")
async def get_vitals():
    """
    Get database vitals: QPS, Cache Hit Ratio, Active Connections.
    """
    vitals = await metric_service.fetch_vitals()
    return vitals

@router.get("/db-info")
async def get_db_info():
    """
    Get database information: version, extensions, size, etc.
    """
    db_info = await metric_service.fetch_db_info()
    return db_info

@router.post("/reset")
async def reset_metrics():
    """
    Reset pg_stat_statements statistics.
    """
    success = await metric_service.reset_stats()
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reset statistics or extension not enabled")
    return {"status": "success", "message": "Statistics reset successfully"}
