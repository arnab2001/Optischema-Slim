"""
Pydantic models for OptiSchema backend.
Defines data structures for query metrics, analysis results, and recommendations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class QueryMetrics(BaseModel):
    """Model for PostgreSQL query metrics from pg_stat_statements."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    queryid: str = Field(..., description="Postgres Query ID (BigInt as String)")
    query_text: str = Field(..., description="The actual SQL query text")
    total_time: int = Field(..., description="Total time spent executing this query (microseconds)")
    calls: int = Field(..., description="Number of times this query was executed")
    mean_time: float = Field(..., description="Mean execution time (microseconds)")
    stddev_time: Optional[float] = Field(None, description="Standard deviation of execution time")
    min_time: Optional[int] = Field(None, description="Minimum execution time")
    max_time: Optional[int] = Field(None, description="Maximum execution time")
    rows: Optional[int] = Field(None, description="Total number of rows retrieved or affected")
    shared_blks_hit: Optional[int] = Field(None, description="Shared blocks hit")
    shared_blks_read: Optional[int] = Field(None, description="Shared blocks read")
    shared_blks_written: Optional[int] = Field(None, description="Shared blocks written")
    shared_blks_dirtied: Optional[int] = Field(None, description="Shared blocks dirtied")
    temp_blks_read: Optional[int] = Field(None, description="Temporary blocks read")
    temp_blks_written: Optional[int] = Field(None, description="Temporary blocks written")
    blk_read_time: Optional[float] = Field(None, description="Time spent reading blocks")
    blk_write_time: Optional[float] = Field(None, description="Time spent writing blocks")
    performance_score: Optional[int] = Field(None, ge=0, le=100, description="Performance score (0-100)")
    time_percentage: Optional[float] = Field(None, description="Percentage of total database time")
    
    model_config = ConfigDict(from_attributes=True)


class ExecutionPlan(BaseModel):
    """Model for PostgreSQL execution plan analysis."""
    
    plan_json: Dict[str, Any] = Field(..., description="Raw execution plan JSON")
    total_cost: Optional[float] = Field(None, description="Total cost of the plan")
    total_time: Optional[float] = Field(None, description="Estimated total time")
    planning_time: Optional[float] = Field(None, description="Planning time")
    execution_time: Optional[float] = Field(None, description="Execution time")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Plan nodes")


class AnalysisResult(BaseModel):
    """Model for query analysis results."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    id: Optional[UUID] = Field(None, description="Unique identifier")
    queryid: str = Field(..., description="Postgres Query ID (BigInt as String)")
    query_text: str = Field(..., description="The SQL query text")
    execution_plan: Optional[ExecutionPlan] = Field(None, description="Execution plan analysis")
    analysis_summary: Optional[str] = Field(None, description="AI-generated analysis summary")
    performance_score: Optional[int] = Field(None, ge=0, le=100, description="Performance score (0-100)")
    bottleneck_type: Optional[str] = Field(None, description="Type of performance bottleneck")
    bottleneck_details: Optional[Dict[str, Any]] = Field(None, description="Detailed bottleneck information")
    created_at: Optional[datetime] = Field(None, description="Analysis timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class Recommendation(BaseModel):
    """Model for optimization recommendations."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    id: Optional[UUID] = Field(None, description="Unique identifier")
    queryid: str = Field(..., description="Postgres Query ID (BigInt as String)")
    recommendation_type: str = Field(..., description="Type of recommendation (index, rewrite, config)")
    title: str = Field(..., description="Short title for the recommendation")
    description: str = Field(..., description="Detailed description of the recommendation")
    sql_fix: Optional[str] = Field(None, description="SQL to apply the fix")
    original_sql: Optional[str] = Field(None, description="Original query SQL")
    patch_sql: Optional[str] = Field(None, description="Optimized query SQL")
    execution_plan_json: Optional[Dict[str, Any]] = Field(None, description="Execution plan for table extraction")
    estimated_improvement_percent: Optional[int] = Field(None, ge=0, le=100, description="Estimated improvement percentage")
    confidence_score: Optional[int] = Field(None, ge=0, le=100, description="Confidence in the recommendation (0-100)")
    risk_level: Optional[str] = Field(None, description="Risk level (low, medium, high)")
    status: str = Field(default="pending", description="Status of the recommendation (pending, active, applied, dismissed)")
    applied: bool = Field(default=False, description="Whether the recommendation has been applied")
    applied_at: Optional[datetime] = Field(None, description="When the recommendation was applied")
    created_at: Optional[datetime] = Field(None, description="Recommendation creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class SandboxTest(BaseModel):
    """Model for sandbox test results."""
    
    id: Optional[UUID] = Field(None, description="Unique identifier")
    recommendation_id: UUID = Field(..., description="ID of the tested recommendation")
    original_performance: Dict[str, Any] = Field(..., description="Original query performance metrics")
    optimized_performance: Optional[Dict[str, Any]] = Field(None, description="Optimized query performance metrics")
    improvement_percent: Optional[int] = Field(None, ge=0, description="Actual improvement percentage")
    test_status: str = Field(..., description="Status of the test (pending, running, completed, failed)")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Detailed test results")
    created_at: Optional[datetime] = Field(None, description="Test creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class BenchmarkJob(BaseModel):
    """Model for benchmark job tracking."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    id: str = Field(..., description="Unique job identifier")
    recommendation_id: str = Field(..., description="ID of the recommendation being benchmarked")
    status: str = Field(default="pending", description="Job status (pending, running, completed, failed, error)")
    job_type: str = Field(..., description="Type of job (benchmark, apply, rollback)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    result_json: Optional[Dict[str, Any]] = Field(None, description="Job results")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    
    model_config = ConfigDict(from_attributes=True)


class HotQuery(BaseModel):
    """Model for hot queries (most expensive queries)."""
    
    queryid: str = Field(..., description="Postgres Query ID (BigInt as String)")
    query_text: str = Field(..., description="The SQL query text")
    total_time: int = Field(..., description="Total execution time")
    calls: int = Field(..., description="Number of calls")
    mean_time: float = Field(..., description="Mean execution time")
    percentage_of_total_time: float = Field(..., description="Percentage of total database time")
    
    model_config = ConfigDict(from_attributes=True)


class MetricsSummary(BaseModel):
    """Model for aggregated metrics summary."""
    
    total_queries: int = Field(..., description="Total number of unique queries")
    total_execution_time: int = Field(..., description="Total execution time across all queries")
    average_query_time: float = Field(..., description="Average execution time per query")
    slowest_query: Optional[HotQuery] = Field(None, description="Slowest query")
    most_called_query: Optional[HotQuery] = Field(None, description="Most frequently called query")
    top_queries: List[HotQuery] = Field(default_factory=list, description="Top N most expensive queries")
    last_updated: datetime = Field(..., description="Last metrics update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class HealthCheck(BaseModel):
    """Model for health check response."""
    
    status: str = Field(..., description="Health status (healthy, unhealthy)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database: bool = Field(..., description="Database connection status")
    openai: bool = Field(..., description="OpenAI API status")
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="Application uptime in seconds")


class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""
    
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


# API Response models
class APIResponse(BaseModel):
    """Base model for API responses."""
    
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class MetricsResponse(APIResponse):
    """Response model for metrics endpoints."""
    
    data: Optional[MetricsSummary] = Field(None, description="Metrics summary data")


class RecommendationsResponse(APIResponse):
    """Response model for recommendations endpoints."""
    
    data: Optional[List[Recommendation]] = Field(None, description="List of recommendations")


class AnalysisResponse(APIResponse):
    """Response model for analysis endpoints."""
    
    data: Optional[AnalysisResult] = Field(None, description="Analysis result data") 


class AuditLog(BaseModel):
    """Model for audit logging of all system actions."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    id: Optional[UUID] = Field(None, description="Unique identifier")
    action_type: str = Field(..., description="Type of action (recommendation_applied, benchmark_run, index_dropped, etc.)")
    user_id: Optional[str] = Field(None, description="User who performed the action")
    recommendation_id: Optional[UUID] = Field(None, description="Related recommendation ID if applicable")
    queryid: Optional[str] = Field(None, description="Related query ID (BigInt as String) if applicable")
    
    # Performance metrics
    before_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics before action")
    after_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics after action")
    improvement_percent: Optional[float] = Field(None, description="Percentage improvement achieved")
    
    # Action details
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional action details")
    risk_level: Optional[str] = Field(None, description="Risk level of the action")
    status: str = Field(default="completed", description="Action status (completed, failed, rolled_back)")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Action timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ConnectionBaseline(BaseModel):
    """Model for storing connection latency baselines."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    id: Optional[UUID] = Field(None, description="Unique identifier")
    connection_id: str = Field(..., description="Unique connection identifier")
    connection_name: str = Field(..., description="Human-readable connection name")
    baseline_latency_ms: float = Field(..., description="Baseline network latency in milliseconds")
    measured_at: datetime = Field(..., description="When baseline was measured")
    connection_config: Dict[str, Any] = Field(..., description="Connection configuration (host, port, etc.)")
    is_active: bool = Field(default=True, description="Whether this baseline is currently active")
    
    model_config = ConfigDict(from_attributes=True)


class IndexRecommendation(BaseModel):
    """Model for unused/redundant index recommendations."""
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    id: Optional[UUID] = Field(None, description="Unique identifier")
    index_name: str = Field(..., description="Name of the index")
    table_name: str = Field(..., description="Name of the table")
    schema_name: str = Field(..., description="Name of the schema")
    size_bytes: int = Field(..., description="Index size in bytes")
    size_pretty: str = Field(..., description="Human-readable index size")
    idx_scan: int = Field(..., description="Number of index scans")
    idx_tup_read: int = Field(..., description="Number of tuples read from index")
    idx_tup_fetch: int = Field(..., description="Number of tuples fetched from index")
    last_used: Optional[datetime] = Field(None, description="When index was last used")
    days_unused: int = Field(..., description="Number of days since last use")
    estimated_savings_mb: float = Field(..., description="Estimated disk space savings in MB")
    risk_level: str = Field(..., description="Risk level (low, medium, high)")
    recommendation_type: str = Field(..., description="Type of recommendation (drop, analyze)")
    sql_fix: Optional[str] = Field(None, description="SQL to drop the index")
    created_at: Optional[datetime] = Field(None, description="Recommendation creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class TableBloatIssue(BaseModel):
    """Model for table bloat issues."""
    
    schema: str = Field(..., description="Schema name")
    table: str = Field(..., description="Table name")
    dead_ratio: float = Field(..., description="Percentage of dead tuples")
    live_tuples: int = Field(..., description="Number of live tuples")
    dead_tuples: int = Field(..., description="Number of dead tuples")
    last_autovacuum: Optional[str] = Field(None, description="Last autovacuum timestamp")
    vacuum_overdue: bool = Field(..., description="Whether vacuum is overdue")
    severity: str = Field(..., description="Severity level (low, medium, high)")
    recommendation: str = Field(..., description="Recommendation text")


class IndexIssue(BaseModel):
    """Model for index issues."""
    
    schema: str = Field(..., description="Schema name")
    table: str = Field(..., description="Table name")
    index: str = Field(..., description="Index name")
    scans: int = Field(..., description="Number of index scans")
    tuples_read: int = Field(..., description="Number of tuples read")
    tuples_fetched: int = Field(..., description="Number of tuples fetched")
    size: str = Field(..., description="Human-readable index size")
    size_bytes: int = Field(..., description="Index size in bytes")
    severity: str = Field(..., description="Severity level")
    recommendation: str = Field(..., description="Recommendation text")


class ConfigIssue(BaseModel):
    """Model for configuration issues."""
    
    setting: str = Field(..., description="Configuration setting name")
    current_value: str = Field(..., description="Current value")
    severity: str = Field(..., description="Severity level (low, medium, high)")
    issue: str = Field(..., description="Description of the issue")
    recommendation: str = Field(..., description="Recommendation text")


class HealthScanResult(BaseModel):
    """Model for health scan results."""
    
    scan_timestamp: str = Field(..., description="When the scan was performed")
    health_score: int = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    table_bloat: Dict[str, Any] = Field(..., description="Table bloat check results")
    index_bloat: Dict[str, Any] = Field(..., description="Index bloat check results")
    config_issues: Dict[str, Any] = Field(..., description="Configuration check results")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    error: Optional[str] = Field(None, description="Error message if scan failed")
    
    model_config = ConfigDict(from_attributes=True) 
class HealthThresholds(BaseModel):
    """Model for health check thresholds."""
    
    # Bloat Thresholds
    bloat_min_size_mb: int = Field(default=100, description="Don't alert if table is smaller than this")
    bloat_min_ratio_percent: int = Field(default=20, description="Don't alert if bloat is < 20%")
    
    # Index Thresholds
    index_unused_min_size_mb: int = Field(default=10, description="Ignore tiny indexes")
    
    # Query Thresholds
    query_slow_ms: int = Field(default=100, description="What counts as slow")
    query_high_impact_percent: int = Field(default=20, description="Query takes up > 20% of total DB time")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "bloat_min_size_mb": 100,
                "bloat_min_ratio_percent": 20,
                "index_unused_min_size_mb": 10,
                "query_slow_ms": 100,
                "query_high_impact_percent": 20
            }
        }
    )
