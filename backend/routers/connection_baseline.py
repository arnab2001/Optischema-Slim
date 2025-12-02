"""
Connection baseline router for OptiSchema backend.
Provides endpoints for measuring and managing connection latency baselines.
"""

from fastapi import APIRouter, HTTPException, Body, Header
from typing import Dict, Any, Optional
from connection_baseline import ConnectionBaselineService

router = APIRouter()

@router.post("/connection-baseline/measure")
async def measure_connection_latency(
    connection_config: Dict[str, Any] = Body(..., description="Database connection configuration"),
    connection_name: str = Body(..., description="Human-readable connection name"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> Dict[str, Any]:
    """Measure connection latency and store baseline"""
    try:
        result = await ConnectionBaselineService.measure_and_store_baseline(
            connection_config,
            connection_name,
            tenant_id=tenant_id,
        )
        if result["success"]:
            return {
                "success": True,
                "message": f"Connection baseline measured and stored for {connection_name}",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"Failed to measure connection latency: {result.get('error', 'Unknown error')}",
                "error": result.get('error', 'Unknown error')
            }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {
            "success": False,
            "message": f"Failed to measure connection latency: {str(e)}",
            "error": str(e),
            "details": error_details
        }

@router.get("/connection-baseline/baselines")
async def get_all_baselines(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Get all active connection baselines"""
    try:
        baselines = await ConnectionBaselineService.get_all_baselines(tenant_id=tenant_id)
        return {"success": True, "data": baselines, "count": len(baselines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get baselines: {str(e)}")

@router.get("/connection-baseline/baseline/{connection_id}")
async def get_baseline(connection_id: str, tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Get specific connection baseline"""
    try:
        baseline = await ConnectionBaselineService.get_baseline(connection_id, tenant_id=tenant_id)
        if baseline:
            return {"success": True, "data": baseline}
        else:
            raise HTTPException(status_code=404, detail="Baseline not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get baseline: {str(e)}")

@router.post("/connection-baseline/update")
async def update_baseline(
    connection_id: str = Body(..., description="Connection ID"),
    baseline_latency_ms: float = Body(..., description="New baseline latency in milliseconds"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
):
    """Update an existing connection baseline"""
    try:
        success = await ConnectionBaselineService.update_baseline(
            connection_id,
            baseline_latency_ms,
            tenant_id=tenant_id,
        )
        if success:
            return {
                "success": True,
                "message": f"Baseline updated for connection {connection_id}",
                "data": {"connection_id": connection_id, "latency_ms": baseline_latency_ms}
            }
        else:
            raise HTTPException(status_code=404, detail="Baseline not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update baseline: {str(e)}")

@router.delete("/connection-baseline/baseline/{connection_id}")
async def deactivate_baseline(connection_id: str, tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Deactivate a connection baseline"""
    try:
        success = await ConnectionBaselineService.deactivate_baseline(connection_id, tenant_id=tenant_id)
        if success:
            return {
                "success": True,
                "message": f"Baseline deactivated for connection {connection_id}"
            }
        else:
            raise HTTPException(status_code=404, detail="Baseline not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate baseline: {str(e)}")

@router.get("/connection-baseline/summary")
async def get_baseline_summary(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Get connection baseline summary statistics"""
    try:
        summary = await ConnectionBaselineService.get_baseline_summary(tenant_id=tenant_id)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get baseline summary: {str(e)}") 
