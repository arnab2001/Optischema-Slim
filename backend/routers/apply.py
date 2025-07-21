from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import logging

from apply_manager import get_apply_manager
from recommendations_db import RecommendationsDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apply", tags=["apply"])


@router.post("/cleanup")
async def cleanup_old_schemas(background_tasks: BackgroundTasks, max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up old temporary schemas.
    
    Args:
        max_age_hours: Maximum age of schemas to keep (default: 24)
        
    Returns:
        Cleanup operation results
    """
    try:
        apply_manager = get_apply_manager()
        
        # Run cleanup in background
        async def cleanup_task():
            cleaned_count = await apply_manager.cleanup_old_schemas(max_age_hours)
            logger.info(f"Background cleanup completed: {cleaned_count} schemas cleaned")
        
        background_tasks.add_task(cleanup_task)
        
        return {
            "success": True,
            "message": f"Cleanup task started for schemas older than {max_age_hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Failed to start cleanup task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{recommendation_id}")
async def apply_recommendation(recommendation_id: str) -> Dict[str, Any]:
    """
    Apply a recommendation by executing DDL changes on the sandbox database.
    
    Args:
        recommendation_id: ID of the recommendation to apply
        
    Returns:
        Apply operation results
    """
    try:
        apply_manager = get_apply_manager()
        result = await apply_manager.apply_recommendation(recommendation_id)
        
        logger.info(f"Successfully applied recommendation: {recommendation_id}")
        return {
            "success": True,
            "message": "Recommendation applied successfully",
            "data": result
        }
        
    except ValueError as e:
        logger.warning(f"Invalid request to apply recommendation {recommendation_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except RuntimeError as e:
        logger.error(f"Failed to apply recommendation {recommendation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error applying recommendation {recommendation_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{recommendation_id}/rollback")
async def rollback_recommendation(recommendation_id: str) -> Dict[str, Any]:
    """
    Rollback an applied recommendation.
    
    Args:
        recommendation_id: ID of the recommendation to rollback
        
    Returns:
        Rollback operation results
    """
    try:
        apply_manager = get_apply_manager()
        result = await apply_manager.rollback_recommendation(recommendation_id)
        
        logger.info(f"Successfully rolled back recommendation: {recommendation_id}")
        return {
            "success": True,
            "message": "Recommendation rolled back successfully",
            "data": result
        }
        
    except ValueError as e:
        logger.warning(f"Invalid request to rollback recommendation {recommendation_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except RuntimeError as e:
        logger.error(f"Failed to rollback recommendation {recommendation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error rolling back recommendation {recommendation_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/changes")
async def get_applied_changes() -> Dict[str, Any]:
    """
    Get list of all applied changes.
    
    Returns:
        List of applied changes
    """
    try:
        apply_manager = get_apply_manager()
        changes = await apply_manager.get_applied_changes()
        
        return {
            "success": True,
            "data": {
                "changes": changes,
                "count": len(changes)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get applied changes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/changes/{recommendation_id}")
async def get_change_status(recommendation_id: str) -> Dict[str, Any]:
    """
    Get status of a specific applied change.
    
    Args:
        recommendation_id: ID of the recommendation
        
    Returns:
        Change status information
    """
    try:
        apply_manager = get_apply_manager()
        change_status = await apply_manager.get_change_status(recommendation_id)
        
        if not change_status:
            raise HTTPException(status_code=404, detail="Change not found")
        
        return {
            "success": True,
            "data": change_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get change status for {recommendation_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def get_apply_manager_status() -> Dict[str, Any]:
    """
    Get the status of the apply manager.
    
    Returns:
        Apply manager status information
    """
    try:
        apply_manager = get_apply_manager()
        changes = await apply_manager.get_applied_changes()
        
        # Count changes by status
        status_counts = {}
        for change in changes:
            status = change.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "success": True,
            "data": {
                "total_changes": len(changes),
                "status_counts": status_counts,
                "available_operations": ["apply", "rollback", "cleanup"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get apply manager status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 