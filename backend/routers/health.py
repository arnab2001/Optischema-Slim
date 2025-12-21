from fastapi import APIRouter, HTTPException
from services.health_scan_service import health_scan_service
from storage import get_latest_health_result
from typing import Dict, Any

router = APIRouter(
    prefix="/api/health",
    tags=["health"]
)

from pydantic import BaseModel

class ScanRequest(BaseModel):
    limit: int = 50

@router.post("/scan")
async def run_health_check(request: ScanRequest = ScanRequest()):
    return await health_scan_service.run_scan(limit=request.limit)
    if "error" in report:
        raise HTTPException(status_code=500, detail=report["error"])
    return report

@router.get("/latest")
async def get_latest_report():
    report = await get_latest_health_result()
    if not report:
        raise HTTPException(status_code=404, detail="No health scan results found")
    return report

@router.get("/history")
async def get_history_reports(limit: int = 10):
    from storage import get_health_history
    return await get_health_history(limit)
