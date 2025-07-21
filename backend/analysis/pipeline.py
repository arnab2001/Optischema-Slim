"""
Analysis pipeline for OptiSchema backend.
Coordinates query analysis and execution plan analysis on a scheduled basis.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from models import QueryMetrics, AnalysisResult, ExecutionPlan
from collector import get_metrics_cache
from .core import analyze_queries, identify_hot_queries, detect_basic_issues
from .explain import analyze_execution_plan, get_plan_summary
from config import settings
from recommendations import generate_recommendations
from utils import calculate_performance_score

logger = logging.getLogger(__name__)

# Global cache for analysis results
analysis_cache: List[AnalysisResult] = []
last_analysis_time: Optional[datetime] = None
recommendations_cache: List[Any] = []


async def run_analysis_pipeline() -> Dict[str, Any]:
    """
    Run the complete analysis pipeline on current query metrics.
    
    Returns:
        Analysis results with performance insights and recommendations
    """
    global analysis_cache, last_analysis_time, recommendations_cache
    
    try:
        logger.info("Starting analysis pipeline...")
        
        # Get current metrics
        metrics = get_metrics_cache()
        if not metrics:
            logger.warning("No metrics available for analysis")
            return {}
        
        # Run core analysis
        core_analysis = analyze_queries(metrics)
        
        # Get hot queries for detailed analysis
        hot_queries = identify_hot_queries(metrics, limit=5)  # Analyze top 5
        
        # Analyze execution plans for hot queries
        detailed_analyses = []
        for hot_query in hot_queries:
            try:
                # Analyze execution plan
                execution_plan = await analyze_execution_plan(hot_query.query_text)
                
                # Detect basic issues
                basic_issues = detect_basic_issues(hot_query.query_text)
                
                # Create analysis result
                analysis_result = AnalysisResult(
                    query_hash=hot_query.query_hash,
                    query_text=hot_query.query_text,
                    execution_plan=execution_plan,
                    analysis_summary=generate_analysis_summary(hot_query, execution_plan, basic_issues),
                    performance_score=calculate_performance_score(hot_query, execution_plan),
                    bottleneck_type=identify_bottleneck_type(execution_plan, basic_issues),
                    bottleneck_details=get_bottleneck_details(execution_plan, basic_issues),
                    created_at=datetime.utcnow()
                )
                
                detailed_analyses.append(analysis_result)
                
            except Exception as e:
                logger.error(f"Failed to analyze query {hot_query.query_hash}: {e}")
                continue
        
        # Update cache
        analysis_cache = detailed_analyses
        last_analysis_time = datetime.utcnow()
        
        # Generate recommendations for all analyses and store them simply
        new_recommendations = await generate_recommendations(detailed_analyses)
        
        # Store in simple store (deduplication is built-in)
        try:
            from simple_recommendations import SimpleRecommendationStore
            stored_count = 0
            for rec in new_recommendations:
                rec_dict = rec.model_dump() if hasattr(rec, 'model_dump') else rec
                rec_id = SimpleRecommendationStore.add_recommendation(rec_dict)
                if rec_id:
                    stored_count += 1
            
            logger.info(f"✅ Stored {stored_count} new recommendations in simple store")
            # Update cache reference for compatibility
            recommendations_cache = new_recommendations
        except Exception as e:
            logger.error(f"Failed to store recommendations: {e}")
            recommendations_cache = new_recommendations
        
        # Prepare results
        results = {
            'core_analysis': core_analysis,
            'detailed_analyses': [analysis.model_dump() for analysis in detailed_analyses],
            'recommendations': [rec.model_dump() for rec in recommendations_cache],
            'analysis_timestamp': last_analysis_time.isoformat(),
            'total_queries_analyzed': len(metrics),
            'hot_queries_analyzed': len(detailed_analyses)
        }
        
        logger.info(f"Analysis pipeline complete: {len(detailed_analyses)} detailed analyses")
        return results
        
    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}")
        return {}


def generate_analysis_summary(hot_query: Any, execution_plan: Optional[ExecutionPlan], basic_issues: List[Dict[str, Any]]) -> str:
    """
    Generate a human-readable analysis summary.
    
    Args:
        hot_query: Hot query information
        execution_plan: Execution plan analysis
        basic_issues: Basic issues detected
        
    Returns:
        Analysis summary text
    """
    summary_parts = []
    
    # Performance overview
    summary_parts.append(f"Query executed {hot_query.calls} times with total time {hot_query.total_time}ms")
    summary_parts.append(f"Average execution time: {hot_query.mean_time:.2f}ms")
    summary_parts.append(f"Represents {hot_query.percentage_of_total_time:.1f}% of total database time")
    
    # Execution plan insights
    if execution_plan:
        plan_summary = get_plan_summary(execution_plan)
        if plan_summary.get('key_insights'):
            summary_parts.append("Key insights:")
            for insight in plan_summary['key_insights'][:3]:  # Top 3 insights
                summary_parts.append(f"- {insight}")
    
    # Basic issues
    if basic_issues:
        summary_parts.append("Detected issues:")
        for issue in basic_issues[:3]:  # Top 3 issues
            summary_parts.append(f"- {issue['description']}")
    
    return "\n".join(summary_parts)


def identify_bottleneck_type(execution_plan: Optional[ExecutionPlan], basic_issues: List[Dict[str, Any]]) -> Optional[str]:
    """
    Identify the primary bottleneck type.
    
    Args:
        execution_plan: Execution plan analysis
        basic_issues: Basic issues detected
        
    Returns:
        Primary bottleneck type
    """
    if not execution_plan:
        return None
    
    plan_summary = get_plan_summary(execution_plan)
    
    # Check for sequential scans
    for insight in plan_summary.get('key_insights', []):
        if 'sequential scan' in insight.lower():
            return 'sequential_scan'
    
    # Check for large sorts
    for insight in plan_summary.get('key_insights', []):
        if 'sort operation' in insight.lower():
            return 'large_sort'
    
    # Check for missing indexes
    for issue in basic_issues:
        if issue['type'] == 'missing_index':
            return 'missing_index'
    
    # Check for SELECT *
    for issue in basic_issues:
        if issue['type'] == 'select_star':
            return 'inefficient_select'
    
    return 'general_performance'


def get_bottleneck_details(execution_plan: Optional[ExecutionPlan], basic_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get detailed bottleneck information.
    
    Args:
        execution_plan: Execution plan analysis
        basic_issues: Basic issues detected
        
    Returns:
        Detailed bottleneck information
    """
    details = {
        'execution_plan_issues': [],
        'basic_issues': basic_issues,
        'recommendations': []
    }
    
    if execution_plan:
        plan_summary = get_plan_summary(execution_plan)
        details['execution_plan_issues'] = plan_summary.get('key_insights', [])
        details['recommendations'].extend(plan_summary.get('recommendations', []))
    
    # Add recommendations from basic issues
    for issue in basic_issues:
        if 'recommendation' in issue:
            details['recommendations'].append(issue['recommendation'])
    
    return details


async def start_analysis_scheduler():
    """
    Start the analysis scheduler that runs analysis periodically.
    """
    logger.info("Starting analysis scheduler...")
    
    while True:
        try:
            # Run analysis pipeline
            await run_analysis_pipeline()
            
            # Wait for next analysis interval
            await asyncio.sleep(settings.analysis_interval)
            
        except asyncio.CancelledError:
            logger.info("Analysis scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Analysis scheduler error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


def get_analysis_cache() -> List[AnalysisResult]:
    """Get the latest analysis results from cache."""
    return analysis_cache


def get_last_analysis_time() -> Optional[datetime]:
    """Get the timestamp of the last analysis run."""
    return last_analysis_time 


def get_recommendations_cache() -> List[Any]:
    """Get the latest recommendations from cache as dictionaries."""
    if not recommendations_cache:
        return []
    return [rec.model_dump() if hasattr(rec, 'model_dump') else rec for rec in recommendations_cache] 