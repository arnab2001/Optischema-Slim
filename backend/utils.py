"""
Utility functions for OptiSchema backend.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def calculate_performance_score(hot_query: Any, execution_plan: Optional[Any] = None) -> int:
    """
    Calculate a unified performance score (0-100) for the query.
    This combines execution time, frequency, cache efficiency, and row processing efficiency.
    
    Args:
        hot_query: Hot query information with metrics
        execution_plan: Execution plan analysis (optional)
        
    Returns:
        Performance score (0-100, higher is better)
    """
    score = 100
    
    # Penalize based on execution time (similar to frontend)
    if hot_query.mean_time > 10:
        score -= min(40, (hot_query.mean_time - 10) / 2)
    
    # Penalize based on frequency (backend logic)
    if hot_query.calls > 1000:
        score -= 20
    elif hot_query.calls > 100:
        score -= 10
    
    # Penalize based on percentage of total time (similar to frontend)
    if hot_query.percentage_of_total_time > 10:
        score -= min(20, (hot_query.percentage_of_total_time - 10) * 0.5)
    
    # Penalize low cache hit rate (frontend logic)
    if hasattr(hot_query, 'shared_blks_hit') and hasattr(hot_query, 'shared_blks_read'):
        total_blocks = hot_query.shared_blks_hit + hot_query.shared_blks_read
        cache_hit = (hot_query.shared_blks_hit / total_blocks * 100) if total_blocks > 0 else 100
        if cache_hit < 95:
            score -= (95 - cache_hit) * 0.5
    
    # Bonus for efficient row processing (frontend logic)
    if hasattr(hot_query, 'rows') and hasattr(hot_query, 'shared_blks_read'):
        if hot_query.rows > 0 and hot_query.shared_blks_read > 0:
            row_efficiency = min(100, (hot_query.rows / (hot_query.shared_blks_read * 8192 / 100)) * 100)
            if row_efficiency > 80:
                score += min(10, (row_efficiency - 80) * 0.2)
    
    # Adjust based on execution plan (backend logic)
    if execution_plan:
        try:
            plan_summary = get_plan_summary(execution_plan)
            if plan_summary.get('performance_rating') == 'poor':
                score -= 20
            elif plan_summary.get('performance_rating') == 'fair':
                score -= 10
        except Exception as e:
            logger.warning(f"Failed to analyze execution plan for performance score: {e}")
    
    return int(max(0, min(100, score)))


def get_plan_summary(execution_plan: Any) -> dict:
    """
    Get a summary of execution plan analysis.
    
    Args:
        execution_plan: Execution plan data
        
    Returns:
        Plan summary dictionary
    """
    # Simple implementation - can be enhanced later
    return {
        'performance_rating': 'good',  # Default to good
        'key_insights': [],
        'recommendations': []
    } 