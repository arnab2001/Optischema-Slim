"""
Analysis Router for OptiSchema Slim.
Handles EXPLAIN plans and 3-Tier Analysis (Index, Rewrite, Advisory).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

from connection_manager import connection_manager
from services.analysis_orchestrator import analysis_orchestrator

router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"]
)

class AnalyzeRequest(BaseModel):
    query: str

class ExplainRequest(BaseModel):
    query: str

@router.post("/analyze")
async def analyze_query(request: AnalyzeRequest):
    """
    Analyze a query using the 3-Tier Strategy (Index, Rewrite, Advisory).
    """
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
    return result

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