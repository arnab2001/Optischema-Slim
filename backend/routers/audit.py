"""
Audit router for OptiSchema backend.
Provides endpoints for audit log retrieval and export.
"""

import csv
import io
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from audit import AuditService

router = APIRouter()

@router.get("/audit/logs")
async def get_audit_logs(
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, description="Maximum number of records"),
    offset: int = Query(0, description="Number of records to skip")
):
    """Get audit logs with optional filtering"""
    try:
        logs = AuditService.get_audit_logs(
            action_type=action_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return {"success": True, "data": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")

@router.get("/audit/logs/export")
async def export_audit_logs(
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    format: str = Query("csv", description="Export format (csv or json)")
):
    """Export audit logs as CSV or JSON"""
    try:
        logs = AuditService.get_audit_logs(
            action_type=action_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        if format.lower() == "csv":
            # Create CSV
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
            )
        else:
            return {"success": True, "data": logs, "count": len(logs)}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")

@router.get("/audit/summary")
async def get_audit_summary():
    """Get audit log summary statistics"""
    try:
        summary = AuditService.get_audit_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit summary: {str(e)}")

@router.get("/audit/action-types")
async def get_audit_action_types():
    """Get list of unique action types in audit logs"""
    try:
        logs = AuditService.get_audit_logs(limit=10000)
        action_types = list(set(log['action_type'] for log in logs))
        return {"success": True, "data": sorted(action_types)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get action types: {str(e)}")

@router.get("/audit/users")
async def get_audit_users():
    """Get list of unique users in audit logs"""
    try:
        logs = AuditService.get_audit_logs(limit=10000)
        users = list(set(log['user_id'] for log in logs if log['user_id']))
        return {"success": True, "data": sorted(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}") 