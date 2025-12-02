"""
Recommendation generation for OptiSchema backend.
Combines heuristics and AI to generate actionable optimization suggestions.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import QueryMetrics, Recommendation, AnalysisResult
from analysis.core import detect_basic_issues
from analysis.explain import get_plan_summary
from analysis.llm import generate_recommendation, rewrite_query
from tenant_context import TenantContext

logger = logging.getLogger(__name__)


def score_recommendation(analysis: AnalysisResult) -> int:
    """
    Score a recommendation based on performance impact and confidence.
    """
    score = 50
    # Heuristic: penalize for low performance score
    if analysis.performance_score is not None:
        score += int(analysis.performance_score / 2)
    # Heuristic: boost for detected bottlenecks
    if analysis.bottleneck_type in ("sequential_scan", "missing_index", "large_sort"):
        score += 20
    # Cap between 0 and 100
    return max(0, min(100, score))


def estimate_improvement(analysis: AnalysisResult) -> int:
    """
    Estimate the percent improvement if the recommendation is applied.
    """
    # Simple heuristic: higher for high-impact bottlenecks
    if analysis.bottleneck_type == "sequential_scan":
        return 50
    if analysis.bottleneck_type == "missing_index":
        return 40
    if analysis.bottleneck_type == "large_sort":
        return 20
    if analysis.performance_score is not None and analysis.performance_score < 50:
        return 10
    return 5


def parse_improvement(val: Any) -> int:
    """Parse estimated improvement value which might be a range or string."""
    try:
        val_str = str(val).rstrip('%').strip()
        if '-' in val_str:
            parts = val_str.split('-')
            return int((float(parts[0]) + float(parts[1])) / 2)
        return int(float(val_str))
    except (ValueError, TypeError):
        return 0


async def generate_recommendations_for_analysis(analysis: AnalysisResult) -> List[Recommendation]:
    """
    Generate recommendations for a single analysis result.
    Prioritizes quality over quantity - one excellent recommendation per query.
    """
    recs: List[Recommendation] = []
    
    # AI-powered recommendation (primary - try this first)
    try:
        ai_rec = await generate_recommendation({
            "query_text": analysis.query_text,
            "bottleneck_type": analysis.bottleneck_type,
            "performance_score": analysis.performance_score,
            "summary": analysis.analysis_summary,
            "actual_metrics": getattr(analysis, 'actual_metrics', None)
        })
        
        # Create AI recommendation
        ai_recommendation = Recommendation(
            tenant_id=analysis.tenant_id,
            id=str(uuid.uuid4()),
            query_hash=analysis.query_hash,
            recommendation_type=ai_rec.get("recommendation_type", "ai"),
            title=ai_rec.get("title", "AI Optimization Suggestion"),
            description=ai_rec.get("description", ""),
            sql_fix=ai_rec.get("sql_fix"),
            estimated_improvement_percent=parse_improvement(ai_rec.get("estimated_improvement", "0")) if ai_rec.get("estimated_improvement") != "Unknown" else estimate_improvement(analysis),
            confidence_score=ai_rec.get("confidence", 75),
            risk_level=ai_rec.get("risk_level", "medium").lower(),
            applied=False,
            created_at=datetime.utcnow()
        )
        recs.append(ai_recommendation)
        
        # If AI provided executable SQL, we're done - no need for heuristic duplicates
        if ai_rec.get("sql_fix"):
            logger.info(f"Generated executable AI recommendation for {analysis.query_hash[:8]}...")
            return recs
        else:
            logger.info(f"Generated advisory AI recommendation for {analysis.query_hash[:8]}...")
    
    except Exception as e:
        logger.warning(f"AI recommendation failed for {analysis.query_hash}: {e}")
    
    # Fallback to heuristic recommendations only if AI failed or provided no executable SQL
    if not recs or not recs[0].sql_fix:
        # Attempt to craft schema-aware SQL if plan/table details are present
        def build_index_sql_from_plan() -> Optional[str]:
            try:
                if not analysis.execution_plan:
                    return None
                summary = get_plan_summary(analysis.execution_plan)
                # Try to infer an index suggestion from insights if a filter is present
                for node in analysis.execution_plan.nodes:
                    relation = node.get('relation_name') or ''
                    filter_cond = node.get('filter') or ''
                    sort_key = node.get('sort_key') or []
                    if relation and filter_cond:
                        # Extremely simple extraction of column names from filter
                        import re
                        cols = list({m.group(2) for m in re.finditer(r'(?:"?([A-Za-z_][A-Za-z0-9_]*)"?\.)?"?([A-Za-z_][A-Za-z0-9_]*)"?', filter_cond)})
                        cols = [c for c in cols if c.lower() not in {'and','or','not'}]
                        if cols:
                            cols_sql = ', '.join(f'"{c}"' for c in cols[:3])
                            return f'CREATE INDEX IF NOT EXISTS idx_{relation}_auto ON "{relation}" ({cols_sql});'
                    if relation and sort_key:
                        keys_sql = ', '.join(sort_key[:3]) if isinstance(sort_key, list) else str(sort_key)
                        return f'CREATE INDEX IF NOT EXISTS idx_{relation}_order ON "{relation}" ({keys_sql});'
            except Exception:
                return None
            return None

        sql_from_plan = build_index_sql_from_plan()

        # Generate ONE best heuristic recommendation based on bottleneck type
        if analysis.bottleneck_type in ("sequential_scan", "missing_index"):
            recs.append(Recommendation(
                tenant_id=analysis.tenant_id,
                id=str(uuid.uuid4()),
                query_hash=analysis.query_hash,
                recommendation_type="index",
                title="Add Index to Improve Performance",
                description=f"This query shows signs of {analysis.bottleneck_type}. Consider adding an index to improve query performance. Analyze the WHERE and JOIN clauses to identify the best columns for indexing.",
                sql_fix=sql_from_plan,
                estimated_improvement_percent=estimate_improvement(analysis),
                confidence_score=score_recommendation(analysis),
                risk_level="low",
                applied=False,
                created_at=datetime.utcnow()
            ))
        elif analysis.bottleneck_type == "large_sort":
            recs.append(Recommendation(
                tenant_id=analysis.tenant_id,
                id=str(uuid.uuid4()),
                query_hash=analysis.query_hash,
                recommendation_type="index",
                title="Add Index for ORDER BY Performance",
                description="This query performs large sorts. Consider adding an index on the ORDER BY columns to eliminate the sort operation and improve performance.",
                sql_fix=sql_from_plan,
                estimated_improvement_percent=estimate_improvement(analysis),
                confidence_score=score_recommendation(analysis),
                risk_level="low",
                applied=False,
                created_at=datetime.utcnow()
            ))
        else:
            # For other bottleneck types, create a generic optimization recommendation
            recs.append(Recommendation(
                tenant_id=analysis.tenant_id,
                id=str(uuid.uuid4()),
                query_hash=analysis.query_hash,
                recommendation_type="optimization",
                title="Query Optimization Opportunity",
                description=f"This query shows performance issues related to {analysis.bottleneck_type}. Consider reviewing the query structure, indexes, and data access patterns.",
                sql_fix=None,
                estimated_improvement_percent=estimate_improvement(analysis),
                confidence_score=score_recommendation(analysis),
                risk_level="medium",
                applied=False,
                created_at=datetime.utcnow()
            ))
    
    # Ensure we always return exactly one recommendation per query
    return recs[:1]


async def generate_recommendations(analyses: List[AnalysisResult]) -> List[Recommendation]:
    """
    Generate recommendations for a list of analysis results.
    """
    all_recs: List[Recommendation] = []
    for analysis in analyses:
        recs = await generate_recommendations_for_analysis(analysis)
        all_recs.extend(recs)
    return all_recs


async def apply_recommendation(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a recommendation (placeholder implementation).
    In a real implementation, this would execute the SQL fix or apply the optimization.
    """
    try:
        # For now, just mark as applied and return success
        # TODO: Implement actual recommendation application logic
        recommendation_type = recommendation.get("type", "unknown")
        sql_fix = recommendation.get("sql_fix")
        
        if sql_fix:
            # TODO: Execute the SQL fix in a sandbox environment
            logger.info(f"Would apply SQL fix: {sql_fix}")
        
        return {
            "success": True,
            "message": f"Recommendation '{recommendation.get('title', 'Unknown')}' applied successfully",
            "recommendation_type": recommendation_type,
            "sql_executed": sql_fix,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to apply recommendation: {e}")
        return {
            "success": False,
            "message": f"Failed to apply recommendation: {str(e)}",
            "error": str(e)
        } 