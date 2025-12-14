"""
Health Router for OptiSchema Slim.
Handles database health scan endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import json

from services.health_scan_service import health_scan_service
from storage import get_setting, set_setting
from models import HealthScanResult

router = APIRouter(
    prefix="/api/health",
    tags=["health"]
)


@router.post("/scan", response_model=HealthScanResult)
async def trigger_health_scan() -> Dict[str, Any]:
    """
    Trigger a comprehensive database health scan.
    Returns scan results with bloat, index, and configuration checks.
    """
    try:
        result = await health_scan_service.perform_scan()
        
        # Store scan result in storage for later retrieval
        await set_setting('last_health_scan', json.dumps(result))
        await set_setting('last_health_scan_timestamp', result.get('scan_timestamp', ''))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health scan failed: {str(e)}")


@router.get("/latest", response_model=HealthScanResult)
async def get_latest_scan() -> Dict[str, Any]:
    """
    Get the most recent health scan results.
    """
    try:
        scan_data = await get_setting('last_health_scan')
        if not scan_data:
            raise HTTPException(status_code=404, detail="No health scan results found. Run /api/health/scan first.")
        
        return json.loads(scan_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scan results: {str(e)}")




