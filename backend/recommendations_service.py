"""
Postgres-backed recommendations service for OptiSchema backend.
Stores recommendations in the OptiSchema metadata database (NOT the target database).
The target database is read-only and only used for monitoring.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg

from tenant_context import TenantContext, add_tenant_to_insert_data, add_tenant_to_where_clause
from metadata_db import get_metadata_pool

logger = logging.getLogger(__name__)

class RecommendationsService:
    """Postgres-backed recommendations service with tenant isolation."""
    
    @staticmethod
    async def add_recommendation(recommendation: Dict[str, Any]) -> str:
        """
        Add a recommendation for the current tenant.
        
        Args:
            recommendation: Recommendation data dictionary
            
        Returns:
            str: Recommendation ID
        """
        try:
            
            
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            # Generate ID if not provided
            if not recommendation.get('id'):
                recommendation['id'] = str(uuid.uuid4())
            
            # Add timestamp if not provided
            if not recommendation.get('created_at'):
                recommendation['created_at'] = datetime.utcnow()
            elif isinstance(recommendation['created_at'], str):
                # Convert ISO string back to datetime if needed
                from dateutil import parser
                recommendation['created_at'] = parser.parse(recommendation['created_at'])
            
            # Add tenant context
            recommendation = add_tenant_to_insert_data(recommendation)
            
            async with pool.acquire() as conn:
                # Check for duplicates (same title and sql_fix for this tenant)
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM optischema.recommendations 
                    WHERE tenant_id = $1 AND title = $2 AND sql_fix = $3
                    """,
                    recommendation['tenant_id'],
                    recommendation.get('title'),
                    recommendation.get('sql_fix')
                )
                
                if existing:
                    logger.info(f"⏭️ Skipping duplicate recommendation for tenant {recommendation['tenant_id']}")
                    return existing['id']
                
                # Insert new recommendation
                await conn.execute(
                    """
                    INSERT INTO optischema.recommendations (
                        id, tenant_id, query_hash, recommendation_type, title, description,
                        sql_fix, original_sql, patch_sql, execution_plan_json,
                        estimated_improvement_percent, confidence_score, risk_level,
                        status, applied, applied_at, created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                    )
                    """,
                    recommendation['id'],
                    recommendation['tenant_id'],
                    recommendation.get('query_hash'),
                    recommendation.get('recommendation_type'),
                    recommendation.get('title'),
                    recommendation.get('description'),
                    recommendation.get('sql_fix'),
                    recommendation.get('original_sql'),
                    recommendation.get('patch_sql'),
                    recommendation.get('execution_plan_json'),
                    recommendation.get('estimated_improvement_percent'),
                    recommendation.get('confidence_score'),
                    recommendation.get('risk_level'),
                    recommendation.get('status', 'pending'),
                    recommendation.get('applied', False),
                    recommendation.get('applied_at'),
                    recommendation['created_at']
                )
                
                logger.info(f"✅ Added recommendation {recommendation['id']} for tenant {recommendation['tenant_id']}")
                return recommendation['id']
                
        except Exception as e:
            logger.error(f"Failed to add recommendation: {e}")
            raise
    
    @staticmethod
    async def get_all_recommendations() -> List[Dict[str, Any]]:
        """
        Get all recommendations for the current tenant.
        
        Returns:
            List of recommendation dictionaries
        """
        try:
            
            
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM optischema.recommendations 
                    WHERE tenant_id = $1 
                    ORDER BY created_at DESC
                    """,
                    tenant_id
                )
                
                recommendations = []
                for row in rows:
                    rec = dict(row)
                    # Convert UUID to string for JSON serialization
                    rec['id'] = str(rec['id'])
                    rec['tenant_id'] = str(rec['tenant_id'])
                    recommendations.append(rec)
                
                logger.info(f"📊 Retrieved {len(recommendations)} recommendations for tenant {tenant_id}")
                return recommendations
                
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            raise
    
    @staticmethod
    async def get_recommendation(rec_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific recommendation by ID for the current tenant.
        
        Args:
            rec_id: Recommendation ID
            
        Returns:
            Recommendation dictionary or None if not found
        """
        try:
            
            
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM optischema.recommendations 
                    WHERE tenant_id = $1 AND id = $2
                    """,
                    tenant_id,
                    rec_id
                )
                
                if row:
                    rec = dict(row)
                    # Convert UUID to string for JSON serialization
                    rec['id'] = str(rec['id'])
                    rec['tenant_id'] = str(rec['tenant_id'])
                    logger.info(f"✅ Found recommendation {rec_id} for tenant {tenant_id}")
                    return rec
                else:
                    logger.warning(f"❌ Recommendation {rec_id} not found for tenant {tenant_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get recommendation {rec_id}: {e}")
            raise
    
    @staticmethod
    async def update_recommendation(rec_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a recommendation by ID for the current tenant.
        
        Args:
            rec_id: Recommendation ID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated, False if not found
        """
        try:
            
            
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            # Build update query dynamically
            set_clauses = []
            values = [tenant_id, rec_id]
            param_count = 2
            
            for key, value in updates.items():
                if key not in ['id', 'tenant_id', 'created_at']:  # Don't allow updating these
                    param_count += 1
                    set_clauses.append(f"{key} = ${param_count}")
                    
                    # Handle datetime strings
                    if key in ['applied_at', 'updated_at'] and isinstance(value, str):
                        try:
                            from dateutil import parser
                            value = parser.parse(value)
                        except Exception:
                            pass  # Keep as string if parsing fails
                    
                    # Handle JSON fields
                    if isinstance(value, (dict, list)):
                        import json
                        value = json.dumps(value)
                            
                    values.append(value)
            
            if not set_clauses:
                logger.warning(f"No valid fields to update for recommendation {rec_id}")
                return False
            
            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            
            query = f"""
                UPDATE optischema.recommendations 
                SET {', '.join(set_clauses)}
                WHERE tenant_id = $1 AND id = $2
            """
            
            async with pool.acquire() as conn:
                result = await conn.execute(query, *values)
                
                if result == "UPDATE 1":
                    logger.info(f"✅ Updated recommendation {rec_id} for tenant {tenant_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Recommendation {rec_id} not found for update in tenant {tenant_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update recommendation {rec_id}: {e}")
            raise
    
    @staticmethod
    async def clear_all() -> int:
        """
        Clear all recommendations for the current tenant.
        
        Returns:
            Number of recommendations deleted
        """
        try:
            
            
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM optischema.recommendations WHERE tenant_id = $1",
                    tenant_id
                )
                
                # Extract count from result string like "DELETE 5"
                count = int(result.split()[-1]) if result.startswith("DELETE") else 0
                logger.info(f"🗑️ Cleared {count} recommendations for tenant {tenant_id}")
                return count
                
        except Exception as e:
            logger.error(f"Failed to clear recommendations: {e}")
            raise
    
    @staticmethod
    async def get_count() -> int:
        """
        Get total count of recommendations for the current tenant.
        
        Returns:
            Number of recommendations
        """
        try:
            
            
            pool = await get_metadata_pool()
            if not pool:
                raise Exception("No metadata database connection available")
            
            tenant_id = TenantContext.get_tenant_id_or_default()
            
            async with pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM optischema.recommendations WHERE tenant_id = $1",
                    tenant_id
                )
                
                return count
                
        except Exception as e:
            logger.error(f"Failed to get recommendation count: {e}")
            raise
    
    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        """
        Get storage statistics for the current tenant.
        
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
                    "SELECT COUNT(*) FROM optischema.recommendations WHERE tenant_id = $1",
                    tenant_id
                )
                
                # Get type breakdown
                type_rows = await conn.fetch(
                    """
                    SELECT recommendation_type, COUNT(*) as count
                    FROM optischema.recommendations 
                    WHERE tenant_id = $1
                    GROUP BY recommendation_type
                    """,
                    tenant_id
                )
                
                types = {row['recommendation_type']: row['count'] for row in type_rows}
                
                return {
                    'total_recommendations': total,
                    'storage_type': 'postgres_tenant_isolated',
                    'types': types,
                    'tenant_id': tenant_id,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get recommendation stats: {e}")
            raise

