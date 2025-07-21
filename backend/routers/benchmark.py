"""
Benchmark router for OptiSchema backend.
Provides endpoints for benchmark job management.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import logging

from job_manager import (
    submit_job, 
    get_job_status, 
    list_jobs, 
    cancel_job, 
    cleanup_old_jobs,
    get_job_manager_status
)
from recommendations_db import RecommendationsDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/{recommendation_id}")
async def create_benchmark_job(recommendation_id: str) -> Dict[str, Any]:
    """
    Create a new benchmark job for a recommendation.
    
    Args:
        recommendation_id: ID of the recommendation to benchmark
        
    Returns:
        Job creation response with job ID
    """
    try:
        # Verify recommendation exists
        recommendation = RecommendationsDB.get_recommendation(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Submit benchmark job
        job_id = await submit_job(recommendation_id, 'benchmark')
        
        return {
            "success": True,
            "message": "Benchmark job created successfully",
            "job_id": job_id,
            "recommendation_id": recommendation_id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create benchmark job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create benchmark job: {str(e)}")


@router.get("/{job_id}")
async def get_benchmark_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status and results of a benchmark job.
    
    Args:
        job_id: Job ID to check
        
    Returns:
        Job status and results
    """
    try:
        job = await get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "success": True,
            "job": job
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.get("/{job_id}/patch.sql")
async def get_patch_sql(job_id: str) -> Dict[str, Any]:
    """
    Get the SQL patch for a benchmark job.
    
    Args:
        job_id: Job ID
        
    Returns:
        SQL patch content
    """
    try:
        job = await get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get recommendation details
        recommendation = RecommendationsDB.get_recommendation(job['recommendation_id'])
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Recommendation not found")
        
        # Generate patch SQL
        patch_sql = recommendation.get('sql_fix', '')
        if not patch_sql:
            patch_sql = "-- No SQL patch available for this recommendation"
        
        # Add rollback comment
        rollback_comment = f"""
-- Rollback SQL (if needed):
-- {recommendation.get('rollback_sql', '-- No rollback SQL available')}
"""
        
        full_patch = f"""
-- OptiSchema Patch for Recommendation: {recommendation['id']}
-- Job ID: {job_id}
-- Created: {job['created_at']}
-- Status: {job['status']}

{patch_sql}

{rollback_comment}
"""
        
        return {
            "success": True,
            "job_id": job_id,
            "recommendation_id": job['recommendation_id'],
            "patch_sql": full_patch,
            "content_type": "application/sql"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patch SQL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get patch SQL: {str(e)}")


@router.post("/{job_id}/cancel")
async def cancel_benchmark_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel a running benchmark job.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        Cancellation result
    """
    try:
        success = await cancel_job(job_id)
        
        if success:
            return {
                "success": True,
                "message": f"Job {job_id} cancelled successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Job {job_id} could not be cancelled (not running or not found)"
            }
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/")
async def list_benchmark_jobs(status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """
    List benchmark jobs with optional filtering.
    
    Args:
        status: Filter by status (pending, running, completed, failed, error, cancelled)
        limit: Maximum number of jobs to return
        
    Returns:
        List of benchmark jobs
    """
    try:
        jobs = await list_jobs(status=status, limit=limit)
        
        return {
            "success": True,
            "jobs": jobs,
            "total": len(jobs),
            "filters": {
                "status": status,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.post("/cleanup")
async def cleanup_benchmark_jobs(hours: int = 24) -> Dict[str, Any]:
    """
    Clean up old completed benchmark jobs.
    
    Args:
        hours: Age threshold in hours (default: 24)
        
    Returns:
        Cleanup result
    """
    try:
        cleaned_count = await cleanup_old_jobs(hours)
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} old jobs",
            "cleaned_count": cleaned_count,
            "age_threshold_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup jobs: {str(e)}")


@router.get("/status/manager")
async def get_job_manager_status_endpoint() -> Dict[str, Any]:
    """
    Get job manager status and statistics.
    
    Returns:
        Job manager status information
    """
    try:
        status = get_job_manager_status()
        
        return {
            "success": True,
            "job_manager": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get job manager status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job manager status: {str(e)}")


@router.post("/{recommendation_id}/apply")
async def create_apply_job(recommendation_id: str) -> Dict[str, Any]:
    """
    Create an apply job for a recommendation.
    
    Args:
        recommendation_id: ID of the recommendation to apply
        
    Returns:
        Job creation response with job ID
    """
    try:
        # Verify recommendation exists
        recommendation = RecommendationsDB.get_recommendation(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Check if recommendation has SQL fix
        if not recommendation.get('sql_fix'):
            raise HTTPException(status_code=400, detail="Recommendation has no SQL fix to apply")
        
        # Submit apply job
        job_id = await submit_job(recommendation_id, 'apply')
        
        return {
            "success": True,
            "message": "Apply job created successfully",
            "job_id": job_id,
            "recommendation_id": recommendation_id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create apply job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create apply job: {str(e)}")


@router.post("/{recommendation_id}/rollback")
async def create_rollback_job(recommendation_id: str) -> Dict[str, Any]:
    """
    Create a rollback job for a recommendation.
    
    Args:
        recommendation_id: ID of the recommendation to rollback
        
    Returns:
        Job creation response with job ID
    """
    try:
        # Verify recommendation exists
        recommendation = RecommendationsDB.get_recommendation(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Check if recommendation was applied
        if not recommendation.get('applied'):
            raise HTTPException(status_code=400, detail="Recommendation has not been applied")
        
        # Submit rollback job
        job_id = await submit_job(recommendation_id, 'rollback')
        
        return {
            "success": True,
            "message": "Rollback job created successfully",
            "job_id": job_id,
            "recommendation_id": recommendation_id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create rollback job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create rollback job: {str(e)}")


@router.get("/schemas/active")
async def list_active_schemas() -> Dict[str, Any]:
    """
    List all active temporary schemas.
    
    Returns:
        List of active schemas with their information
    """
    try:
        from schema_manager import get_schema_manager
        schema_manager = get_schema_manager()
        schemas = await schema_manager.list_active_schemas()
        
        return {
            "success": True,
            "schemas": schemas,
            "total": len(schemas)
        }
        
    except Exception as e:
        logger.error(f"Failed to list active schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list active schemas: {str(e)}")


@router.post("/schemas/cleanup")
async def cleanup_orphaned_schemas() -> Dict[str, Any]:
    """
    Clean up orphaned temporary schemas.
    
    Returns:
        Cleanup result
    """
    try:
        from schema_manager import get_schema_manager
        schema_manager = get_schema_manager()
        cleaned_count = await schema_manager.cleanup_orphaned_schemas()
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} orphaned schemas",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup orphaned schemas: {str(e)}")


@router.get("/schemas/{job_id}")
async def get_schema_info(job_id: str) -> Dict[str, Any]:
    """
    Get information about a specific temporary schema.
    
    Args:
        job_id: Job ID to get schema info for
        
    Returns:
        Schema information
    """
    try:
        from schema_manager import get_schema_manager
        schema_manager = get_schema_manager()
        schema_info = await schema_manager.get_schema_info(job_id)
        
        if not schema_info:
            raise HTTPException(status_code=404, detail=f"Schema for job {job_id} not found")
        
        return {
            "success": True,
            "schema": schema_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema info: {str(e)}")


@router.get("/replica/status")
async def get_replica_status() -> Dict[str, Any]:
    """
    Get replica database status and configuration.
    
    Returns:
        Replica status information
    """
    try:
        from replica_manager import get_replica_manager
        replica_manager = get_replica_manager()
        replica_info = await replica_manager.get_replica_info()
        
        return {
            "success": True,
            "replica": replica_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get replica status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get replica status: {str(e)}")


@router.post("/replica/health-check")
async def check_replica_health() -> Dict[str, Any]:
    """
    Perform a manual replica health check.
    
    Returns:
        Health check result
    """
    try:
        from replica_manager import get_replica_manager
        replica_manager = get_replica_manager()
        
        is_healthy = await replica_manager.check_health()
        
        return {
            "success": True,
            "healthy": is_healthy,
            "message": "Replica is healthy" if is_healthy else "Replica is unhealthy"
        }
        
    except Exception as e:
        logger.error(f"Failed to check replica health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check replica health: {str(e)}")


@router.post("/replica/initialize")
async def initialize_replica() -> Dict[str, Any]:
    """
    Initialize replica connection.
    
    Returns:
        Initialization result
    """
    try:
        from replica_manager import initialize_replica_manager
        await initialize_replica_manager()
        
        return {
            "success": True,
            "message": "Replica manager initialized successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize replica: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize replica: {str(e)}") 