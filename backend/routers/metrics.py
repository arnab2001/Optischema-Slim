"""
Metrics router for OptiSchema backend.
Provides endpoints for query metrics and performance data.
"""

from fastapi import APIRouter, HTTPException, Query, Header
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from analysis.core import calculate_performance_metrics, identify_hot_queries
from collector import get_metrics_cache
from tenant_context import resolve_tenant_id
from connection_manager import connection_manager

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/raw")
async def get_raw_metrics(
    limit: int = Query(100, ge=1, le=5000, description="Number of queries to return"),
    offset: int = Query(0, ge=0, description="Number of queries to skip"),
    sort_by: str = Query("total_time", description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    min_calls: int = Query(1, ge=1, description="Minimum number of calls"),
    min_time: float = Query(0.0, ge=0.0, description="Minimum mean execution time (ms)"),
    search: Optional[str] = Query(None, description="Search query text"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> Dict[str, Any]:
    """Return paginated query metrics with filtering and sorting."""
    # Check if we're connected to a database
    is_connected = await connection_manager.check_connection_health()
    if not is_connected:
        return {
            "queries": [],
            "pagination": {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False
            }
        }
    
    metrics = get_metrics_cache(tenant_id)
    if not metrics:
        return {
            "queries": [],
            "pagination": {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False
            }
        }
    
    # Convert Pydantic models to dictionaries
    metrics_data = [metric.model_dump() if hasattr(metric, 'model_dump') else metric for metric in metrics]
    
    # Apply filters
    filtered_metrics = []
    for metric in metrics_data:
        # Filter by minimum calls
        if metric.get('calls', 0) < min_calls:
            continue
            
        # Filter by minimum time
        if metric.get('mean_time', 0.0) < min_time:
            continue
            
        # Filter by search term
        if search and search.lower() not in metric.get('query_text', '').lower():
            continue
            
        filtered_metrics.append(metric)
    
    # Validate sort_by parameter
    valid_sort_fields = ["total_time", "mean_time", "calls", "rows", "time_percentage", "performance_score"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Must be one of: {valid_sort_fields}")
    
    # Sort metrics
    reverse = order == "desc"
    sorted_metrics = sorted(filtered_metrics, key=lambda x: x.get(sort_by, 0), reverse=reverse)
    
    # Apply pagination
    total = len(sorted_metrics)
    start = offset
    end = offset + limit
    paginated_metrics = sorted_metrics[start:end]
    
    return {
        "queries": paginated_metrics,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": end < total,
            "returned": len(paginated_metrics)
        },
        "filters": {
            "min_calls": min_calls,
            "min_time": min_time,
            "search": search
        }
    }


@router.get("/summary")
async def get_metrics_summary(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Dict[str, Any]:
    """Return aggregated metrics summary."""
    metrics = get_metrics_cache(tenant_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics available")
    
    summary = calculate_performance_metrics(metrics)
    
    # Add data size information
    summary["data_size"] = {
        "total_queries": len(metrics),
        "cache_size_mb": len(str(metrics)) / 1024 / 1024  # Rough estimate
    }
    
    return summary


@router.get("/hot")
async def get_hot_queries(
    limit: int = Query(10, ge=1, le=100),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> List[Dict[str, Any]]:
    """Return the most expensive queries."""
    metrics = get_metrics_cache(tenant_id)
    if not metrics:
        return []
    
    hot_queries = identify_hot_queries(metrics, limit=limit)
    # Convert Pydantic models to dictionaries
    return [query.model_dump() if hasattr(query, 'model_dump') else query for query in hot_queries]


@router.get("/top")
async def get_top_queries(
    limit: int = Query(10, ge=1, le=100), 
    sort_by: str = Query("total_time"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> List[Dict[str, Any]]:
    """Return top queries sorted by specified criteria."""
    metrics = get_metrics_cache(tenant_id)
    if not metrics:
        return []
    
    # Validate sort_by parameter
    valid_sort_fields = ["total_time", "mean_time", "calls", "rows"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Must be one of: {valid_sort_fields}")
    
    # Sort metrics by the specified field
    sorted_metrics = sorted(metrics, key=lambda x: x.get(sort_by, 0), reverse=True)
    # Convert Pydantic models to dictionaries
    return [metric.model_dump() if hasattr(metric, 'model_dump') else metric for metric in sorted_metrics[:limit]]


@router.get("/stats")
async def get_collection_stats(tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> Dict[str, Any]:
    """Return collection statistics and performance info."""
    metrics = get_metrics_cache(tenant_id)
    
    if not metrics:
        return {
            "total_queries": 0,
            "collection_status": "no_data",
            "memory_usage": "0 MB",
            "last_update": None
        }
    
    # Calculate statistics
    total_queries = len(metrics)
    total_calls = sum(m.calls if hasattr(m, 'calls') else m.get('calls', 0) for m in metrics)
    total_time = sum(m.total_time if hasattr(m, 'total_time') else m.get('total_time', 0) for m in metrics)
    
    # Estimate memory usage
    memory_mb = len(str(metrics)) / 1024 / 1024
    
    return {
        "total_queries": total_queries,
        "total_calls": total_calls,
        "total_time_ms": total_time,
        "memory_usage_mb": round(memory_mb, 2),
        "collection_status": "active" if total_queries > 0 else "no_data",
        "performance": {
            "large_dataset": total_queries > 10000,
            "memory_warning": memory_mb > 100,
            "recommendation": get_performance_recommendation(total_queries, memory_mb)
        }
    }


@router.get("/historical")
async def get_historical_metrics(
    time_range: str = Query("1h", description="Time range: 1h, 6h, 24h, 7d"),
    interval: str = Query("5m", description="Data interval: 1m, 5m, 15m, 1h"),
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> Dict[str, Any]:
    """Return historical metrics for trend analysis."""
    # For now, generate mock historical data
    # In a real implementation, this would query a time-series database
    
    now = datetime.utcnow()
    intervals = {
        "1h": 12,  # 5-minute intervals for 1 hour
        "6h": 72,  # 5-minute intervals for 6 hours
        "24h": 288,  # 5-minute intervals for 24 hours
        "7d": 2016  # 5-minute intervals for 7 days
    }
    
    interval_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "1h": 60
    }
    
    num_intervals = intervals.get(time_range, 12)
    interval_min = interval_minutes.get(interval, 5)
    
    # Generate mock historical data
    historical_data = []
    base_latency = 50  # Base latency in ms
    base_queries = 1000  # Base query count
    
    for i in range(num_intervals):
        timestamp = now - timedelta(minutes=i * interval_min)
        
        # Add some realistic variation
        variation = (i % 10) * 0.2  # Cyclic variation
        noise = (hash(str(i)) % 20) - 10  # Random noise
        
        avg_latency = max(10, base_latency + variation * 20 + noise)
        p95_latency = avg_latency * 2.5
        p99_latency = avg_latency * 4
        
        total_queries = max(100, base_queries + (hash(str(i)) % 500) - 250)
        slow_queries = max(0, int(total_queries * 0.1 + (hash(str(i)) % 20) - 10))
        
        historical_data.append({
            "timestamp": timestamp.isoformat(),
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "p99_latency": round(p99_latency, 2),
            "total_queries": total_queries,
            "slow_queries": slow_queries
        })
    
    # Reverse to show oldest first
    historical_data.reverse()
    
    return {
        "time_range": time_range,
        "interval": interval,
        "data_points": len(historical_data),
        "data": historical_data
    }


@router.get("/trends")
async def get_performance_trends() -> Dict[str, Any]:
    """Return performance trend analysis."""
    metrics = get_metrics_cache()
    
    if not metrics:
        return {
            "trends": [],
            "insights": [],
            "recommendations": []
        }
    
    # Calculate trends based on current metrics
    total_queries = len(metrics)
    avg_latency = sum(m.mean_time for m in metrics) / total_queries if total_queries > 0 else 0
    slow_queries = len([m for m in metrics if m.mean_time > 100])
    
    # Generate trend insights
    trends = []
    insights = []
    recommendations = []
    
    if avg_latency > 50:
        trends.append({
            "type": "warning",
            "metric": "average_latency",
            "value": avg_latency,
            "threshold": 50,
            "message": f"Average query latency is {avg_latency:.1f}ms, above recommended threshold"
        })
        recommendations.append("Consider adding indexes on frequently queried columns")
    
    if slow_queries > total_queries * 0.1:
        trends.append({
            "type": "warning",
            "metric": "slow_queries",
            "value": slow_queries,
            "threshold": total_queries * 0.1,
            "message": f"{slow_queries} queries are taking longer than 100ms"
        })
        recommendations.append("Review and optimize slow queries")
    
    # Add positive trends if performance is good
    if avg_latency < 20:
        trends.append({
            "type": "success",
            "metric": "average_latency",
            "value": avg_latency,
            "threshold": 20,
            "message": f"Excellent average query latency: {avg_latency:.1f}ms"
        })
    
    return {
        "trends": trends,
        "insights": insights,
        "recommendations": recommendations,
        "summary": {
            "total_queries": total_queries,
            "avg_latency": round(avg_latency, 2),
            "slow_queries": slow_queries,
            "slow_percentage": round((slow_queries / total_queries) * 100, 1) if total_queries > 0 else 0
        }
    }


@router.get("/export")
async def export_metrics(
    format: str = Query("json", description="Export format: json, csv"),
    include_queries: bool = Query(True, description="Include query text in export"),
    filters: Optional[str] = Query(None, description="JSON string of filters to apply")
) -> Dict[str, Any]:
    """Export metrics data in various formats."""
    metrics = get_metrics_cache()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics available for export")
    
    # Convert to exportable format
    export_data = []
    for metric in metrics:
        export_item = {
            "query_hash": metric.query_hash,
            "total_time": metric.total_time,
            "calls": metric.calls,
            "mean_time": metric.mean_time,
            "rows": metric.rows,
            "performance_score": metric.performance_score,
            "time_percentage": metric.time_percentage
        }
        
        if include_queries:
            export_item["query_text"] = metric.query_text
        
        export_data.append(export_item)
    
    if format == "csv":
        # Generate CSV content
        import csv
        import io
        
        output = io.StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
        
        return {
            "format": "csv",
            "data": output.getvalue(),
            "filename": f"optischema_metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    
    # Default JSON format
    return {
        "format": "json",
        "data": export_data,
        "filename": f"optischema_metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        "total_records": len(export_data)
    }


def get_performance_recommendation(total_queries: int, memory_mb: float) -> str:
    """Get performance recommendations based on data size."""
    if total_queries > 100000:
        return "Very large dataset detected. Consider enabling sampling and increasing min_calls filter."
    elif total_queries > 50000:
        return "Large dataset detected. Consider using pagination and filtering for better performance."
    elif memory_mb > 100:
        return "High memory usage detected. Consider implementing data retention policies."
    elif total_queries > 10000:
        return "Medium dataset size. Pagination recommended for frontend display."
    else:
        return "Dataset size is manageable. No special optimizations needed." 
