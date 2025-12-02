"""
Audit router for OptiSchema backend.
Provides endpoints for audit log retrieval and export.
"""

import csv
import io
from fastapi import APIRouter, Query, HTTPException, Header
from typing import Optional, List
from audit_service import AuditService

router = APIRouter()

@router.get("/audit/logs")
async def get_audit_logs(
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, description="Maximum number of records"),
    offset: int = Query(0, description="Number of records to skip"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
):
    """Get audit logs with optional filtering"""
    try:
        logs = await AuditService.get_audit_logs(
            action_type=action_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            tenant_id=tenant_id
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
    format: str = Query("csv", description="Export format (csv or json)"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
):
    """Export audit logs as CSV or JSON"""
    try:
        logs = await AuditService.get_audit_logs(
            action_type=action_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit for export
            tenant_id=tenant_id
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
async def get_audit_summary(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Get audit log summary statistics"""
    try:
        summary = await AuditService.get_audit_summary(tenant_id=tenant_id)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit summary: {str(e)}")

@router.get("/audit/action-types")
async def get_audit_action_types(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Get list of unique action types in audit logs"""
    try:
        action_types = await AuditService.get_distinct_action_types(tenant_id=tenant_id)
        return {"success": True, "data": sorted(action_types)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get action types: {str(e)}")

@router.get("/audit/users")
async def get_audit_users(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Get list of unique users in audit logs"""
    try:
        users = await AuditService.get_distinct_users(tenant_id=tenant_id)
        return {"success": True, "data": sorted(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}") 
