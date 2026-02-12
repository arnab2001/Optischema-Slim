"""
Core analysis module for OptiSchema backend.
Handles query fingerprinting, hot query identification, and basic heuristics.
"""

import logging
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from models import QueryMetrics, HotQuery, MetricsSummary
from collector import get_metrics_cache

logger = logging.getLogger(__name__)


def fingerprint_query(query_text: str) -> str:
    """
    Create a fingerprint for a query by normalizing whitespace and removing literals.
    
    Args:
        query_text: The raw SQL query text
        
    Returns:
        Normalized query fingerprint
    """
    # Remove comments
    query = re.sub(r'--.*$', '', query_text, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query.strip())
    
    # Replace literal values with placeholders
    # Replace string literals
    query = re.sub(r"'[^']*'", "'?'", query)
    query = re.sub(r'"[^"]*"', '"?"', query)

    # Replace numeric literals BUT preserve LIMIT/OFFSET values
    # (so LIMIT 10 and LIMIT 1000000 remain distinct fingerprints)
    query = re.sub(r'\b\d+\.\d+\b', '?', query)  # Decimal numbers
    # Temporarily protect LIMIT/OFFSET values, then replace remaining integers
    query = re.sub(r'\b(LIMIT\s+)(\d+)\b', r'\1__KEEP_\2__', query, flags=re.IGNORECASE)
    query = re.sub(r'\b(OFFSET\s+)(\d+)\b', r'\1__KEEP_\2__', query, flags=re.IGNORECASE)
    query = re.sub(r'\b\d+\b', '?', query)  # Replace all other integers
    query = re.sub(r'__KEEP_(\d+)__', r'\1', query)  # Restore LIMIT/OFFSET values
    
    # Replace boolean literals
    query = re.sub(r'\b(true|false|null)\b', '?', query, flags=re.IGNORECASE)
    
    # Normalize case for SQL keywords
    sql_keywords = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'INSERT', 'UPDATE',
        'DELETE', 'CREATE', 'DROP', 'ALTER', 'INDEX', 'TABLE', 'VIEW', 'FUNCTION'
    ]
    
    for keyword in sql_keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        query = re.sub(pattern, keyword, query, flags=re.IGNORECASE)
    
    return query.strip()


def identify_hot_queries(metrics: List[QueryMetrics], limit: int = 10) -> List[HotQuery]:
    """
    Identify the most expensive queries based on total execution time.
    
    Args:
        metrics: List of query metrics
        limit: Maximum number of hot queries to return
        
    Returns:
        List of hot queries sorted by total execution time
    """
    if not metrics:
        return []
    
    # Calculate total execution time across all queries
    total_db_time = sum(m.total_time for m in metrics)
    
    # Group queries by fingerprint and aggregate metrics
    query_groups: Dict[str, List[QueryMetrics]] = {}
    for metric in metrics:
        fingerprint = fingerprint_query(metric.query_text)
        if fingerprint not in query_groups:
            query_groups[fingerprint] = []
        query_groups[fingerprint].append(metric)
    
    # Aggregate metrics for each query group
    hot_queries = []
    for fingerprint, group_metrics in query_groups.items():
        total_time = sum(m.total_time for m in group_metrics)
        total_calls = sum(m.calls for m in group_metrics)
        mean_time = total_time / total_calls if total_calls > 0 else 0
        
        # Calculate percentage of total database time
        percentage = (total_time / total_db_time * 100) if total_db_time > 0 else 0
        
        # Use queryid from first metric in group (or generate hash if not available)
        first_metric = group_metrics[0]
        queryid = getattr(first_metric, 'queryid', None)
        if not queryid:
            # Fallback: generate hash from fingerprint if queryid not available
            queryid = hashlib.md5(fingerprint.encode()).hexdigest()
        
        hot_query = HotQuery(
            queryid=queryid,
            query_text=first_metric.query_text,  # Use first query as representative
            total_time=total_time,
            calls=total_calls,
            mean_time=mean_time,
            percentage_of_total_time=percentage
        )
        hot_queries.append(hot_query)
    
    # Sort by total execution time (descending)
    hot_queries.sort(key=lambda x: x.total_time, reverse=True)
    
    return hot_queries[:limit]


def calculate_performance_metrics(metrics: List[QueryMetrics]) -> MetricsSummary:
    """
    Calculate aggregated performance metrics from query data.
    
    Args:
        metrics: List of query metrics
        
    Returns:
        Aggregated metrics summary
    """
    if not metrics:
        return MetricsSummary(
            total_queries=0,
            total_execution_time=0,
            average_query_time=0.0,
            top_queries=[],
            last_updated=datetime.utcnow()
        )
    
    # Basic aggregations
    total_queries = len(set(fingerprint_query(m.query_text) for m in metrics))
    total_execution_time = sum(m.total_time for m in metrics)
    average_query_time = total_execution_time / len(metrics) if metrics else 0
    
    # Get hot queries
    hot_queries = identify_hot_queries(metrics, limit=10)
    
    # Find slowest and most called queries
    slowest_query = max(metrics, key=lambda x: x.mean_time) if metrics else None
    most_called_query = max(metrics, key=lambda x: x.calls) if metrics else None
    
    # Convert to HotQuery format if needed
    slowest_hot = None
    if slowest_query:
        slowest_hot = HotQuery(
            queryid=getattr(slowest_query, 'queryid', hashlib.md5(slowest_query.query_text.encode()).hexdigest()),
            query_text=slowest_query.query_text,
            total_time=slowest_query.total_time,
            calls=slowest_query.calls,
            mean_time=slowest_query.mean_time,
            percentage_of_total_time=(slowest_query.total_time / total_execution_time * 100) if total_execution_time > 0 else 0
        )
    
    most_called_hot = None
    if most_called_query:
        most_called_hot = HotQuery(
            queryid=getattr(most_called_query, 'queryid', hashlib.md5(most_called_query.query_text.encode()).hexdigest()),
            query_text=most_called_query.query_text,
            total_time=most_called_query.total_time,
            calls=most_called_query.calls,
            mean_time=most_called_query.mean_time,
            percentage_of_total_time=(most_called_query.total_time / total_execution_time * 100) if total_execution_time > 0 else 0
        )
    
    return MetricsSummary(
        total_queries=total_queries,
        total_execution_time=total_execution_time,
        average_query_time=average_query_time,
        slowest_query=slowest_hot,
        most_called_query=most_called_hot,
        top_queries=hot_queries,
        last_updated=datetime.utcnow()
    )


def detect_basic_issues(query_text: str) -> List[Dict[str, Any]]:
    """
    Detect basic performance issues in SQL queries using heuristics.
    
    Args:
        query_text: The SQL query to analyze
        
    Returns:
        List of detected issues with details
    """
    issues = []
    query_upper = query_text.upper()
    
    # Check for SELECT * (potential performance issue)
    if re.search(r'\bSELECT\s+\*', query_upper):
        issues.append({
            'type': 'select_star',
            'severity': 'medium',
            'description': 'Query uses SELECT * which may retrieve unnecessary columns',
            'recommendation': 'Specify only required columns in SELECT clause'
        })
    
    # Check for missing WHERE clause in DELETE/UPDATE
    if re.search(r'\b(DELETE|UPDATE)\s+.*?(?:\bWHERE\b|$)', query_upper, re.IGNORECASE):
        if 'WHERE' not in query_upper:
            issues.append({
                'type': 'missing_where',
                'severity': 'high',
                'description': 'DELETE/UPDATE query missing WHERE clause',
                'recommendation': 'Add WHERE clause to limit affected rows'
            })
    
    # Check for potential N+1 patterns (simplified)
    if query_upper.count('SELECT') > 1:
        issues.append({
            'type': 'multiple_selects',
            'severity': 'low',
            'description': 'Query contains multiple SELECT statements',
            'recommendation': 'Consider using JOINs or subqueries to reduce round trips'
        })
    
    # Check for ORDER BY without LIMIT
    if re.search(r'\bORDER\s+BY\b', query_upper) and not re.search(r'\bLIMIT\b', query_upper):
        issues.append({
            'type': 'order_by_no_limit',
            'severity': 'low',
            'description': 'ORDER BY without LIMIT may sort large result sets',
            'recommendation': 'Add LIMIT clause to restrict result set size'
        })
    
    # Check for LIKE patterns that may not use indexes
    if re.search(r"LIKE\s+'.*%'", query_upper):
        issues.append({
            'type': 'leading_wildcard',
            'severity': 'medium',
            'description': 'LIKE pattern starts with wildcard, may not use indexes',
            'recommendation': 'Consider using full-text search or restructuring the pattern'
        })
    
    return issues


def analyze_queries(metrics: Optional[List[QueryMetrics]] = None) -> Dict[str, Any]:
    """
    Main analysis function that processes query metrics and generates insights.
    
    Args:
        metrics: Optional list of metrics to analyze. If None, uses cached metrics.
        
    Returns:
        Analysis results with performance metrics and insights
    """
    if metrics is None:
        metrics = get_metrics_cache()
    
    logger.info(f"Analyzing {len(metrics)} query metrics")
    
    # Calculate performance metrics
    performance_summary = calculate_performance_metrics(metrics)
    
    # Identify hot queries
    hot_queries = identify_hot_queries(metrics, limit=10)
    
    # Analyze individual queries for issues
    query_issues = {}
    for metric in metrics[:20]:  # Limit to first 20 for performance
        issues = detect_basic_issues(metric.query_text)
        if issues:
            queryid = getattr(metric, 'queryid', hashlib.md5(metric.query_text.encode()).hexdigest())
            query_issues[queryid] = {
                'query_text': metric.query_text,
                'issues': issues
            }
    
    # Generate analysis summary
    analysis_result = {
        'performance_summary': performance_summary.model_dump(),
        'hot_queries': [q.model_dump() for q in hot_queries],
        'query_issues': query_issues,
        'analysis_timestamp': datetime.utcnow().isoformat(),
        'total_queries_analyzed': len(metrics),
        'queries_with_issues': len(query_issues)
    }
    
    logger.info(f"Analysis complete: {len(hot_queries)} hot queries, {len(query_issues)} queries with issues")
    
    return analysis_result 