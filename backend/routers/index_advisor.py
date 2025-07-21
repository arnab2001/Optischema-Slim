"""docker compose build optischema-api
Index advisor router for OptiSchema backend.
Provides endpoints for analyzing and retrieving index recommendations.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional
from index_advisor import IndexAdvisorService

router = APIRouter()

@router.post("/index-advisor/analyze")
async def run_index_analysis(
    connection_config: Dict[str, Any] = Body(..., description="Database connection configuration")
) -> Dict[str, Any]:
    """Run full index analysis and store recommendations"""
    try:
        result = await IndexAdvisorService.run_full_analysis(connection_config)
        if result["success"]:
            return {
                "success": True,
                "message": f"Index analysis completed. Found {result['total_recommendations']} recommendations.",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"Failed to run index analysis: {result.get('error', 'Unknown error')}",
                "error": result.get('error', 'Unknown error')
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to run index analysis: {str(e)}",
            "error": str(e)
        }

@router.get("/index-advisor/recommendations")
async def get_index_recommendations(
    recommendation_type: Optional[str] = Query(None, description="Filter by recommendation type (drop, analyze)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (low, medium, high)"),
    limit: int = Query(100, description="Maximum number of recommendations"),
    offset: int = Query(0, description="Number of recommendations to skip")
):
    """Get index recommendations with optional filtering"""
    try:
        recommendations = IndexAdvisorService.get_index_recommendations(
            recommendation_type=recommendation_type,
            risk_level=risk_level,
            limit=limit,
            offset=offset
        )
        return {"success": True, "data": recommendations, "count": len(recommendations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.get("/index-advisor/recommendations/unused")
async def get_unused_index_recommendations():
    """Get unused index recommendations"""
    try:
        recommendations = IndexAdvisorService.get_index_recommendations(
            recommendation_type="drop",
            limit=1000
        )
        return {"success": True, "data": recommendations, "count": len(recommendations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unused index recommendations: {str(e)}")

@router.get("/index-advisor/recommendations/redundant")
async def get_redundant_index_recommendations():
    """Get redundant index recommendations"""
    try:
        recommendations = IndexAdvisorService.get_index_recommendations(
            recommendation_type="analyze",
            limit=1000
        )
        return {"success": True, "data": recommendations, "count": len(recommendations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get redundant index recommendations: {str(e)}")

@router.get("/index-advisor/summary")
async def get_index_recommendation_summary():
    """Get index recommendation summary statistics"""
    try:
        summary = IndexAdvisorService.get_index_recommendation_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendation summary: {str(e)}")

@router.delete("/index-advisor/recommendations/{recommendation_id}")
async def delete_recommendation(recommendation_id: str):
    """Delete a specific index recommendation"""
    try:
        success = IndexAdvisorService.delete_recommendation(recommendation_id)
        if success:
            return {
                "success": True,
                "message": f"Recommendation {recommendation_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Recommendation not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete recommendation: {str(e)}")

@router.get("/index-advisor/database-stats")
async def get_database_index_stats(
    connection_config: Dict[str, Any] = Body(..., description="Database connection configuration")
):
    """Get database index statistics"""
    try:
        stats = await IndexAdvisorService.get_database_index_stats(connection_config)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")

@router.post("/index-advisor/recommendations/{recommendation_id}/apply")
async def apply_recommendation(
    recommendation_id: str,
    connection_config: Dict[str, Any] = Body(..., description="Database connection configuration")
):
    """Apply a specific index recommendation (placeholder for future implementation)"""
    try:
        # This would require additional implementation to actually execute the SQL
        # For now, we'll return a placeholder response
        return {
            "success": True,
            "message": f"Recommendation {recommendation_id} applied successfully (placeholder)",
            "data": {
                "recommendation_id": recommendation_id,
                "applied_at": "2024-01-01T00:00:00Z",
                "status": "applied"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply recommendation: {str(e)}") 