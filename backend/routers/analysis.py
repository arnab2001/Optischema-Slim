"""
Analysis Router for OptiSchema Slim.
Handles EXPLAIN plans and 3-Tier Analysis (Index, Rewrite, Advisory).
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional
import hashlib
import json
import re

from connection_manager import connection_manager
from services.analysis_orchestrator import analysis_orchestrator
from services.simulation_service import simulation_service
from memory_cache import app_cache, CACHE_ANALYSIS_PREFIX

router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"]
)

class AnalyzeRequest(BaseModel):
    query: str
    scenario_id: Optional[str] = None
    score: Optional[float] = None
    refresh: bool = False
    cache_only: bool = False  # If true, return cached result or 204 (no content) — never run fresh analysis

class ExplainRequest(BaseModel):
    query: str

class VerifyRequest(BaseModel):
    query: str
    sql: str


def _query_cache_key(query: str) -> str:
    """Normalize query text into a stable cache key."""
    normalized = re.sub(r'\s+', ' ', query.strip().lower())
    fingerprint = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{CACHE_ANALYSIS_PREFIX}{fingerprint}"


@router.post("/analyze")
async def analyze_query(request: AnalyzeRequest):
    """
    Analyze a query using the 3-Tier Strategy (Index, Rewrite, Advisory).
    Returns cached result if available (15 min TTL). Pass refresh=true in body to force fresh analysis.
    """
    cache_key = _query_cache_key(request.query)

    # Check cache (skip for benchmark requests — those need fresh results)
    if not request.refresh and not request.scenario_id:
        cached = app_cache.get(cache_key)
        if cached:
            age = app_cache.get_age(cache_key)
            cached["_cached"] = True
            cached["_cache_age_seconds"] = round(age) if age else 0
            return cached

    # cache_only mode: don't run fresh analysis, just return empty
    if request.cache_only:
        return {"_cached": False, "_no_result": True}

    result = await analysis_orchestrator.analyze_query(request.query)

    if "error" in result:
        # Return structured error response with message and suggestion
        error_detail = {
            "error": result["error"],
            "message": result.get("message", result["error"]),
            "suggestion": result.get("suggestion", ""),
            "statement_type": result.get("statement_type")
        }
        raise HTTPException(status_code=400, detail=error_detail)

    # Cache the successful result (15 min TTL)
    app_cache.set(cache_key, result, ttl=900)
    result["_cached"] = False

    # If it's a benchmark request, save to PostgreSQL
    if request.scenario_id:
        from services.benchmark_service import benchmark_service
        # Inject score for storage if provided
        if request.score is not None:
            result["_benchmark_score"] = request.score

        await benchmark_service.save_benchmark_result(
            request.scenario_id,
            request.query,
            result
        )

    return result

@router.get("/verify/{scenario_id}")
async def verify_benchmark(scenario_id: str):
    """
    Verify a benchmark result was stored correctly in PostgreSQL.
    """
    pool = await connection_manager.get_pool()
    if not pool:
        raise HTTPException(status_code=400, detail="No active database connection")
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT actual_category, alignment_score 
                FROM golden.benchmark_results 
                WHERE scenario_id = $1 
                ORDER BY created_at DESC LIMIT 1
            """, scenario_id)
            
            if row:
                return {
                    "scenario_id": scenario_id,
                    "actual_category": row["actual_category"],
                    "alignment_score": row["alignment_score"]
                }
            return {"error": "Benchmark result not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@router.post("/explain")
async def explain_query(request: ExplainRequest):
    """
    Run EXPLAIN (FORMAT JSON) on a query.
    """
    pool = await connection_manager.get_pool()
    if not pool:
        raise HTTPException(status_code=400, detail="No active database connection")
    
    try:
        async with pool.acquire() as conn:
            plan_json = await conn.fetchval(f"EXPLAIN (FORMAT JSON) {request.query}")
            return json.loads(plan_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Explain failed: {str(e)}")

@router.post("/verify")
async def verify_impact(request: VerifyRequest):
    """
    Verify the impact of an index suggestion using HypoPG.
    """
    return await simulation_service.simulate_index(request.query, request.sql)