"""
Postgres-backed analysis results service for OptiSchema backend.
Provides tenant-aware storage and retrieval of query analysis results.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import asyncpg

from tenant_context import TenantContext, add_tenant_to_insert_data
from metadata_db import get_metadata_pool

logger = logging.getLogger(__name__)

class AnalysisResultsService:
    """Postgres-backed analysis results service with tenant isolation."""
    
    @staticmethod
    async def store_analysis_result(analysis: Dict[str, Any]) -> str:
        """
        Store an analysis result for the current tenant.
        
        Args:
            analysis: Analysis result data dictionary
            
        Returns:
            str: Analysis result ID
        """
        try:
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            # Generate ID if not provided
            if not analysis.get('id'):
                analysis['id'] = str(uuid.uuid4())
            
            # Add timestamp if not provided
            if not analysis.get('created_at'):
                analysis['created_at'] = datetime.utcnow()
            
            # Add tenant context
            analysis = add_tenant_to_insert_data(analysis)
            
            async with pool.acquire() as conn:
                # Check for duplicates (same query_hash for this tenant within last hour)
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM optischema.analysis_results 
                    WHERE tenant_id = $1 AND query_hash = $2 
                    AND created_at >= NOW() - INTERVAL '1 hour'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    analysis['tenant_id'],
                    analysis.get('query_hash')
                )
                
                if existing:
                    # Update existing instead of creating duplicate
                    await conn.execute(
                        """
                        UPDATE optischema.analysis_results 
                        SET execution_plan = $1, analysis_summary = $2, 
                            performance_score = $3, bottleneck_type = $4,
                            bottleneck_details = $5, created_at = $6
                        WHERE id = $7
                        """,
                        analysis.get('execution_plan') if isinstance(analysis.get('execution_plan'), str) else json.dumps(analysis.get('execution_plan')) if analysis.get('execution_plan') else None,
                        analysis.get('analysis_summary'),
                        analysis.get('performance_score'),
                        analysis.get('bottleneck_type'),
                        analysis.get('bottleneck_details') if isinstance(analysis.get('bottleneck_details'), str) else json.dumps(analysis.get('bottleneck_details')) if analysis.get('bottleneck_details') else None,
                        analysis['created_at'],
                        existing['id']
                    )
                    logger.info(f"✅ Updated analysis result {existing['id']} for tenant {analysis['tenant_id']}")
                    return str(existing['id'])
                
                # Insert new analysis result
                await conn.execute(
                    """
                    INSERT INTO optischema.analysis_results (
                        id, tenant_id, query_hash, query_text, execution_plan,
                        analysis_summary, performance_score, bottleneck_type,
                        bottleneck_details, created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
                    )
                    """,
                    analysis['id'],
                    analysis['tenant_id'],
                    analysis.get('query_hash'),
                    analysis.get('query_text'),
                    analysis.get('execution_plan') if isinstance(analysis.get('execution_plan'), str) else json.dumps(analysis.get('execution_plan')) if analysis.get('execution_plan') else None,
                    analysis.get('analysis_summary'),
                    analysis.get('performance_score'),
                    analysis.get('bottleneck_type'),
                    analysis.get('bottleneck_details') if isinstance(analysis.get('bottleneck_details'), str) else json.dumps(analysis.get('bottleneck_details')) if analysis.get('bottleneck_details') else None,
                    analysis['created_at']
                )
                
                logger.info(f"✅ Stored analysis result {analysis['id']} for tenant {analysis['tenant_id']}")
                return analysis['id']
                
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")
            raise
    
    @staticmethod
    async def get_recent_analyses(hours: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent analysis results for the current tenant.
        
        Args:
            hours: Number of hours to look back (default: 1)
            limit: Maximum number of results to return (default: 100)
            
        Returns:
            List of analysis result dictionaries
        """
        try:
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM optischema.analysis_results 
                    WHERE tenant_id = $1 
                    AND created_at >= NOW() - INTERVAL '%s hours'
                    ORDER BY created_at DESC
                    LIMIT $2
                    """ % hours,
                    tenant_id,
                    limit
                )
                
                analyses = []
                for row in rows:
                    analysis = dict(row)
                    # Convert UUID to string for JSON serialization
                    analysis['id'] = str(analysis['id'])
                    analysis['tenant_id'] = str(analysis['tenant_id'])
                    analyses.append(analysis)
                
                logger.info(f"📊 Retrieved {len(analyses)} recent analyses for tenant {tenant_id}")
                return analyses
                
        except Exception as e:
            logger.error(f"Failed to get recent analyses: {e}")
            raise
    
    @staticmethod
    async def get_analysis_by_query_hash(query_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent analysis for a specific query hash.
        
        Args:
            query_hash: Query hash to look up
            
        Returns:
            Analysis result dictionary or None if not found
        """
        try:
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM optischema.analysis_results 
                    WHERE tenant_id = $1 AND query_hash = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    tenant_id,
                    query_hash
                )
                
                if row:
                    analysis = dict(row)
                    # Convert UUID to string for JSON serialization
                    analysis['id'] = str(analysis['id'])
                    analysis['tenant_id'] = str(analysis['tenant_id'])
                    logger.info(f"✅ Found analysis for query_hash {query_hash} in tenant {tenant_id}")
                    return analysis
                else:
                    logger.debug(f"No analysis found for query_hash {query_hash} in tenant {tenant_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get analysis for query_hash {query_hash}: {e}")
            raise
    
    @staticmethod
    async def get_analysis_count(hours: int = 24) -> int:
        """
        Get count of analyses for the current tenant within specified hours.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Number of analyses
        """
        try:
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM optischema.analysis_results 
                    WHERE tenant_id = $1 
                    AND created_at >= NOW() - INTERVAL '%s hours'
                    """ % hours,
                    tenant_id
                )
                
                return count or 0
                
        except Exception as e:
            logger.error(f"Failed to get analysis count: {e}")
            raise
    
    @staticmethod
    async def cleanup_old_analyses(days: int = 7) -> int:
        """
        Clean up analysis results older than specified days for all tenants.
        
        Args:
            days: Number of days to keep (default: 7)
            
        Returns:
            Number of analyses deleted
        """
        try:
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            async with pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM optischema.analysis_results 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    """ % days
                )
                
                # Extract count from result string like "DELETE 5"
                count = int(result.split()[-1]) if result.startswith("DELETE") else 0
                if count > 0:
                    logger.info(f"🗑️ Cleaned up {count} old analysis results (older than {days} days)")
                return count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old analyses: {e}")
            raise
    
    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        """
        Get analysis statistics for the current tenant.
        
        Returns:
            Dictionary with statistics
        """
        try:
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM optischema.analysis_results WHERE tenant_id = $1",
                    tenant_id
                )
                
                # Get recent count (last 24 hours)
                recent = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM optischema.analysis_results 
                    WHERE tenant_id = $1 
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    """,
                    tenant_id
                )
                
                # Get bottleneck type breakdown
                bottleneck_rows = await conn.fetch(
                    """
                    SELECT bottleneck_type, COUNT(*) as count
                    FROM optischema.analysis_results 
                    WHERE tenant_id = $1
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY bottleneck_type
                    """,
                    tenant_id
                )
                
                bottlenecks = {row['bottleneck_type']: row['count'] for row in bottleneck_rows if row['bottleneck_type']}
                
                return {
                    'total_analyses': total or 0,
                    'recent_analyses_24h': recent or 0,
                    'bottleneck_breakdown': bottlenecks,
                    'storage_type': 'postgres_tenant_isolated',
                    'tenant_id': tenant_id,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get analysis stats: {e}")
            raise
