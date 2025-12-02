"""
Analysis router for OptiSchema backend.
Provides endpoints for query analysis and analysis status.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from analysis.pipeline import get_analysis_cache, run_analysis_pipeline
from analysis.core import analyze_queries
from analysis.explain import execute_explain_plan, extract_plan_metrics
from db import get_pool

router = APIRouter(prefix="/analysis", tags=["analysis"])


class QueryAnalysisRequest(BaseModel):
    """Request model for query analysis."""
    query: str
    explain: bool = True
    optimize: bool = True


class QueryAnalysisResponse(BaseModel):
    """Response model for query analysis."""
    query: str
    execution_plan: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    optimization: Optional[str] = None
    recommendations: Optional[Dict[str, Any]] = None


from utils import calculate_performance_score as unified_calculate_performance_score

def calculate_performance_score(execution_plan: Optional[Dict[str, Any]], query_text: str) -> int:
    """
    Calculate a performance score based on execution plan analysis.
    Now uses the unified calculation from utils.py for consistency.
    
    Args:
        execution_plan: The execution plan from EXPLAIN
        query_text: The original query text
        
    Returns:
        Performance score from 0-100
    """
    if not execution_plan or execution_plan.get("error"):
        # If no execution plan, use basic heuristics
        return calculate_basic_score(query_text)
    
    try:
        # Extract metrics from execution plan
        metrics = extract_plan_metrics(execution_plan)
        
        # Create a mock hot_query object for the unified calculation
        hot_query = type('HotQuery', (), {
            'mean_time': metrics.get('total_time', 0),
            'calls': 1,  # Default for single query analysis
            'percentage_of_total_time': 0,  # Not available in single query context
            'shared_blks_hit': metrics.get('shared_hit_blocks', 0),
            'shared_blks_read': metrics.get('shared_read_blocks', 0),
            'rows': metrics.get('total_rows', 0)
        })()
        
        # Use the unified calculation
        return unified_calculate_performance_score(hot_query, execution_plan)
        
    except Exception:
        # Fallback to basic score calculation
        return calculate_basic_score(query_text)


def calculate_basic_score(query_text: str) -> int:
    """
    Calculate a basic performance score based on query characteristics.
    
    Args:
        query_text: The query text
        
    Returns:
        Basic performance score from 0-100
    """
    score = 75  # Base score
    
    query_upper = query_text.upper()
    
    # Penalize complex operations
    if 'JOIN' in query_upper:
        score -= 10
    if 'GROUP BY' in query_upper:
        score -= 5
    if 'ORDER BY' in query_upper:
        score -= 5
    if 'DISTINCT' in query_upper:
        score -= 5
    if 'LIKE' in query_upper:
        score -= 5
    
    # Bonus for simple queries
    if query_upper.startswith('SELECT COUNT(*)') or query_upper.startswith('SELECT 1'):
        score += 10
    if 'LIMIT' in query_upper:
        score += 5
    
    # Penalize SELECT *
    if 'SELECT *' in query_upper:
        score -= 10
    
    return max(0, min(100, score))


def detect_bottleneck_type(execution_plan: Optional[Dict[str, Any]], query_text: str) -> str:
    """
    Detect the main bottleneck type based on execution plan and query text.
    
    Args:
        execution_plan: The execution plan from EXPLAIN
        query_text: The original query text
        
    Returns:
        Bottleneck type description
    """
    # First, try to detect based on query text patterns
    query_upper = query_text.upper()
    
    # Check for cursor operations
    if 'MOVE ALL' in query_upper or 'FETCH ALL' in query_upper:
        return "cursor_inefficiency"
    
    # Check for SELECT *
    if 'SELECT *' in query_upper:
        return "inefficient_select"
    
    # Check for complex operations
    if 'JOIN' in query_upper and query_upper.count('JOIN') > 2:
        return "complex_joins"
    
    if 'GROUP BY' in query_upper and 'ORDER BY' in query_upper:
        return "sort_operation"
    
    if 'DISTINCT' in query_upper:
        return "distinct_operation"
    
    if 'LIKE' in query_upper and '%' in query_text:
        return "pattern_matching"
    
    # If we have execution plan, use it for more detailed analysis
    if execution_plan and not execution_plan.get("error"):
        try:
            metrics = extract_plan_metrics(execution_plan)
            nodes = metrics.get('nodes', [])
            
            # Check for sequential scans
            seq_scans = sum(1 for node in nodes if node.get('node_type') == 'Seq Scan')
            if seq_scans > 0:
                return "sequential_scan"
            
            # Check for large sorts
            sorts = sum(1 for node in nodes if node.get('node_type') == 'Sort')
            if sorts > 0:
                return "sort_operation"
            
            # Check for slow execution
            total_time = metrics.get('total_time', 0)
            if total_time > 1000:
                return "slow_execution"
            elif total_time > 100:
                return "moderate_execution"
            
            # Check for high cost
            total_cost = metrics.get('total_cost', 0)
            if total_cost > 10000:
                return "high_cost"
            
            return "efficient"
            
        except Exception:
            pass
    
    # Fallback based on query characteristics
    if 'JOIN' in query_upper:
        return "join_optimization"
    elif 'WHERE' in query_upper:
        return "filter_optimization"
    else:
        return "general_optimization"


@router.get("/latest")
async def get_latest_analysis() -> Dict[str, Any]:
    """Return the latest analysis results."""
    analysis_results = await get_analysis_cache()
    if not analysis_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    return analysis_results


@router.post("/run")
async def run_analysis() -> Dict[str, Any]:
    """Manually trigger analysis pipeline."""
    try:
        results = await run_analysis_pipeline()
        return {
            "success": True,
            "message": "Analysis completed successfully",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/query", response_model=QueryAnalysisResponse)
async def analyze_query(request: QueryAnalysisRequest) -> QueryAnalysisResponse:
    """Analyze a specific query."""
    try:
        pool = get_pool()
        if not pool:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        response = QueryAnalysisResponse(query=request.query)
        
        # Get execution plan if requested
        if request.explain:
            try:
                plan = await execute_explain_plan(request.query)
                response.execution_plan = plan
            except Exception as e:
                # Plan analysis failed, but continue with other analysis
                response.execution_plan = {"error": str(e)}
        
        # Calculate performance score and detect bottlenecks
        try:
            performance_score = calculate_performance_score(response.execution_plan, request.query)
            bottleneck_type = detect_bottleneck_type(response.execution_plan, request.query)
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            performance_score = 50  # Default score
            bottleneck_type = "unknown"
        
        # Analyze the query
        analysis_result = {
            "query_text": request.query,
            "query_hash": hash(request.query),
            "analysis_summary": "Query analysis completed",
            "performance_score": performance_score,
            "bottleneck_type": bottleneck_type
        }
        response.analysis = analysis_result
        
        # Generate optimization if requested
        if request.optimize:
            try:
                from analysis.llm import rewrite_query
                optimized = await rewrite_query(request.query)
                response.optimization = optimized
            except Exception as e:
                response.optimization = f"Optimization failed: {str(e)}"
        
        # Generate recommendations
        try:
            from analysis.llm import generate_recommendation
            from collector import get_metrics_cache
            
            # Try to find actual metrics for this query
            try:
                metrics_cache = get_metrics_cache()
                actual_metrics = None
                if metrics_cache and isinstance(metrics_cache, list):
                    # Look for matching query in metrics cache
                    query_hash = str(hash(request.query))
                    for metric in metrics_cache:
                        if hasattr(metric, 'query_hash') and metric.query_hash == query_hash:
                            actual_metrics = {
                                "total_time": metric.total_time,
                                "calls": metric.calls,
                                "mean_time": metric.mean_time,
                                "stddev_time": metric.stddev_time,
                                "rows": metric.rows,
                                "shared_blks_hit": metric.shared_blks_hit,
                                "shared_blks_read": metric.shared_blks_read,
                                "shared_blks_written": metric.shared_blks_written,
                                "temp_blks_read": metric.temp_blks_read,
                                "temp_blks_written": metric.temp_blks_written,
                                "blk_read_time": metric.blk_read_time,
                                "blk_write_time": metric.blk_write_time,
                                "time_percentage": metric.time_percentage,
                                "performance_score": metric.performance_score
                            }
                            break
            except Exception as e:
                logger.error(f"Error looking up metrics: {e}")
                actual_metrics = None
            
            query_data = {
                "query_text": request.query,
                "analysis": analysis_result,
                "execution_plan": response.execution_plan,
                "actual_metrics": actual_metrics  # Include actual metrics if available
            }
            recommendation = await generate_recommendation(query_data)
            response.recommendations = recommendation
        except Exception as e:
            response.recommendations = {"error": str(e)}
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query analysis failed: {str(e)}")


@router.get("/status")
async def get_analysis_status() -> Dict[str, Any]:
    """Get the current analysis status."""
    analysis_results = await get_analysis_cache()
    
    # analysis_results is now a list of analysis dictionaries
    if analysis_results:
        latest = analysis_results[0] if analysis_results else {}
        return {
            "last_analysis": latest.get("created_at") if latest else None,
            "total_queries_analyzed": len(analysis_results),
            "hot_queries_found": len(analysis_results),
            "recommendations_generated": 0,  # Will be fetched separately if needed
            "analysis_running": False,  # TODO: Implement analysis status tracking
            "next_scheduled": None  # TODO: Implement scheduling status
        }
    else:
        return {
            "last_analysis": None,
            "total_queries_analyzed": 0,
            "hot_queries_found": 0,
            "recommendations_generated": 0,
            "analysis_running": False,
            "next_scheduled": None
        }


@router.get("/history")
async def get_analysis_history(limit: int = 10) -> Dict[str, Any]:
    """Get analysis history (placeholder for future implementation)."""
    # TODO: Implement analysis history storage and retrieval
    return {
        "message": "Analysis history not yet implemented",
        "limit": limit,
        "history": []
    } 