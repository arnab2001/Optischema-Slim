from fastapi import APIRouter, HTTPException, Query
from services.health_scan_service import health_scan_service
from services.schema_health_service import schema_health_service
from storage import (
    get_latest_health_result,
    get_decommission_entries,
    get_decommission_snapshots,
    update_decommission_stage,
    delete_decommission_entry
)
from memory_cache import (
    app_cache,
    CACHE_SCHEMA_HEALTH,
    CACHE_UNUSED_INDEXES,
    CACHE_AI_SCHEMA_SUMMARY,
    CACHE_HEALTH_SCAN
)
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/health",
    tags=["health"]
)

from pydantic import BaseModel

class ScanRequest(BaseModel):
    limit: int = 50

@router.post("/scan")
async def run_health_check(request: ScanRequest = ScanRequest()):
    result = await health_scan_service.run_scan(limit=request.limit)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    # Cache the scan result
    app_cache.set(CACHE_HEALTH_SCAN, result, ttl=300)  # 5 min
    return result

@router.get("/latest")
async def get_latest_report():
    # Try cache first
    cached = app_cache.get(CACHE_HEALTH_SCAN)
    if cached:
        age = app_cache.get_age(CACHE_HEALTH_SCAN)
        cached["_cached"] = True
        cached["_cache_age_seconds"] = round(age) if age else 0
        return cached

    report = await get_latest_health_result()
    if not report:
        raise HTTPException(status_code=404, detail="No health scan results found")
    return report

@router.get("/history")
async def get_history_reports(limit: int = 10):
    from storage import get_health_history
    return await get_health_history(limit)

@router.get("/schema")
async def analyze_schema_health(refresh: bool = Query(False, description="Force fresh scan, bypass cache")):
    """
    Analyze database schema for design issues.
    Returns cached result if available (10 min TTL). Pass ?refresh=true to force rescan.
    """
    if not refresh:
        cached = app_cache.get(CACHE_SCHEMA_HEALTH)
        if cached:
            age = app_cache.get_age(CACHE_SCHEMA_HEALTH)
            cached["_cached"] = True
            cached["_cache_age_seconds"] = round(age) if age else 0
            return cached

    result = await schema_health_service.analyze_database_schema()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    app_cache.set(CACHE_SCHEMA_HEALTH, result, ttl=600)  # 10 min
    result["_cached"] = False
    return result


# ── Unused Index Intelligence ──────────────────────────────────────────

@router.get("/unused-indexes")
async def analyze_unused_indexes(refresh: bool = Query(False)):
    """
    Analyze all indexes with cost-benefit scoring.
    Returns cached result if available (10 min TTL). Pass ?refresh=true to force rescan.
    """
    if not refresh:
        cached = app_cache.get(CACHE_UNUSED_INDEXES)
        if cached:
            age = app_cache.get_age(CACHE_UNUSED_INDEXES)
            cached["_cached"] = True
            cached["_cache_age_seconds"] = round(age) if age else 0
            return cached

    result = await schema_health_service.analyze_unused_indexes()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    app_cache.set(CACHE_UNUSED_INDEXES, result, ttl=600)  # 10 min
    result["_cached"] = False
    return result


# ── AI Schema Summary ──────────────────────────────────────────────────

@router.get("/schema/ai-summary")
async def get_ai_schema_summary(refresh: bool = Query(False)):
    """
    Get an AI-generated summary of schema health issues.
    Uses cached schema health results + LLM analysis.
    Cached for 30 min since it costs tokens.
    """
    if not refresh:
        cached = app_cache.get(CACHE_AI_SCHEMA_SUMMARY)
        if cached:
            age = app_cache.get_age(CACHE_AI_SCHEMA_SUMMARY)
            cached["_cached"] = True
            cached["_cache_age_seconds"] = round(age) if age else 0
            return cached

    # Get schema health data (from cache or fresh)
    schema_data = app_cache.get(CACHE_SCHEMA_HEALTH)
    if not schema_data:
        schema_data = await schema_health_service.analyze_database_schema()
        if "error" in schema_data:
            raise HTTPException(status_code=500, detail=schema_data["error"])
        app_cache.set(CACHE_SCHEMA_HEALTH, schema_data, ttl=600)

    # Get unused index data (from cache or fresh)
    index_data = app_cache.get(CACHE_UNUSED_INDEXES)
    if not index_data:
        index_data = await schema_health_service.analyze_unused_indexes()
        if "error" not in index_data:
            app_cache.set(CACHE_UNUSED_INDEXES, index_data, ttl=600)

    # Build AI prompt from the data
    try:
        from services.llm_service import llm_service
        summary = await _generate_ai_summary(schema_data, index_data)
        result = {"success": True, "summary": summary, "_cached": False}
        app_cache.set(CACHE_AI_SCHEMA_SUMMARY, result, ttl=1800)  # 30 min
        return result
    except Exception as e:
        logger.error(f"AI summary generation failed: {e}")
        return {"success": False, "error": str(e)}


async def _generate_ai_summary(schema_data: Dict, index_data: Dict) -> Dict[str, Any]:
    """Generate AI summary from schema health and index data."""
    from services.llm_service import llm_service

    # Compact the data for the prompt
    issues = schema_data.get("issues", [])
    summary = schema_data.get("summary", {})

    # Build issue summary
    issue_lines = []
    for issue in issues[:20]:  # Limit to top 20 to save tokens
        issue_lines.append(f"- [{issue['severity']}] {issue['message']} ({issue['type']}): {issue['impact']}")

    # Build index summary
    idx_summary = index_data.get("summary", {}) if index_data and "error" not in index_data else {}
    idx_details = []
    if index_data and "indexes" in index_data:
        for idx in index_data["indexes"][:15]:  # Top 15 worst indexes
            if idx["recommended_stage"] != "active":
                idx_details.append(
                    f"- {idx['index_name']} on {idx['table_name']}: "
                    f"score={idx['usefulness_score']}, scans/day={idx['scan_rate_per_day']}, "
                    f"size={idx['size_pretty']}, stage={idx['recommended_stage']}"
                )

    prompt = f"""You are a PostgreSQL performance expert analyzing a database schema.
Given the following schema health data, provide a brief, actionable summary.

## Schema Health Summary
- Tables analyzed: {summary.get('total_tables', 0)}
- Tables with issues: {summary.get('tables_with_issues', 0)}
- Critical (P0): {summary.get('p0_count', 0)}
- High (P1): {summary.get('p1_count', 0)}
- Medium (P2): {summary.get('p2_count', 0)}

## Issues Found
{chr(10).join(issue_lines) if issue_lines else "No issues detected."}

## Index Health
- Drop candidates: {idx_summary.get('drop_candidates', 0)}
- Disable candidates: {idx_summary.get('disable_candidates', 0)}
- Monitoring: {idx_summary.get('monitoring', 0)}
- Reclaimable space: {idx_summary.get('total_reclaimable_pretty', 'N/A')}
- Stats age: {index_data.get('stats_age_days', 'unknown')} days

## Index Details (lowest scoring)
{chr(10).join(idx_details) if idx_details else "All indexes are healthy."}

Respond in JSON with this structure:
{{
  "overall_grade": "A/B/C/D/F",
  "one_liner": "One sentence overall assessment",
  "priorities": [
    {{
      "priority": 1,
      "title": "Short title",
      "description": "What to do and why",
      "impact": "high/medium/low",
      "effort": "quick/moderate/significant"
    }}
  ],
  "quick_wins": ["List of things that can be done immediately"],
  "risks": ["Any risks or things to watch out for"]
}}

Keep priorities to max 5 items, quick_wins to max 3 items, risks to max 3 items.
Be specific — reference actual table/index names from the data."""

    result = await llm_service.get_completion(prompt, json_mode=True)
    return result


# ── Cache Management ───────────────────────────────────────────────────

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    stats = app_cache.stats()
    # Add per-key age info
    keys = {
        "schema_health": CACHE_SCHEMA_HEALTH,
        "unused_indexes": CACHE_UNUSED_INDEXES,
        "ai_summary": CACHE_AI_SCHEMA_SUMMARY,
        "health_scan": CACHE_HEALTH_SCAN
    }
    key_info = {}
    for name, key in keys.items():
        age = app_cache.get_age(key)
        key_info[name] = {
            "cached": age is not None,
            "age_seconds": round(age) if age else None
        }

    return {"success": True, **stats, "keys": key_info}


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cached health data."""
    app_cache.clear()
    return {"success": True, "message": "Cache cleared"}


# ── Decommission Workflow ──────────────────────────────────────────────

class DecommissionRequest(BaseModel):
    indexes: List[Dict[str, Any]]
    database_name: str


@router.post("/decommission/start")
async def start_decommissioning(request: DecommissionRequest):
    """Start monitoring selected indexes for safe decommissioning."""
    result = await schema_health_service.start_decommission(
        indexes=request.indexes,
        database_name=request.database_name
    )
    return {"success": True, **result}


@router.get("/decommission/tracking")
async def get_tracking(database_name: str = None):
    """Get all indexes being tracked for decommissioning."""
    entries = await get_decommission_entries(database_name)
    return {"success": True, "entries": entries}


class StageUpdateRequest(BaseModel):
    decommission_id: int
    new_stage: str
    notes: str = ""


@router.post("/decommission/update-stage")
async def update_stage(request: StageUpdateRequest):
    """Advance or revert the decommissioning stage for an index."""
    valid_stages = {"monitoring", "ready_to_disable", "ready_to_drop", "dropped", "active"}
    if request.new_stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    await update_decommission_stage(request.decommission_id, request.new_stage, request.notes)
    return {"success": True}


@router.post("/decommission/refresh")
async def refresh_snapshots():
    """Take a snapshot of current scan counts for all monitored indexes."""
    result = await schema_health_service.refresh_decommission_snapshots()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"success": True, **result}


@router.get("/decommission/{decommission_id}/snapshots")
async def get_snapshots(decommission_id: int):
    """Get scan count history for a tracked index."""
    snapshots = await get_decommission_snapshots(decommission_id)
    return {"success": True, "snapshots": snapshots}


@router.delete("/decommission/{decommission_id}")
async def remove_tracking(decommission_id: int):
    """Stop tracking an index (remove from decommission list)."""
    await delete_decommission_entry(decommission_id)
    return {"success": True}
