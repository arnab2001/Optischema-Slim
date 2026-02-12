"""
Index advisor service for OptiSchema backend.
Analyzes pg_stat_user_indexes to identify unused and redundant indexes.
"""

import json
import uuid
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

from connection_manager import connection_manager
from tenant_context import TenantContext
from db_utils import configure_ssl

logger = logging.getLogger(__name__)

class IndexAdvisorService:
    """Service for analyzing and recommending index optimizations."""

    @staticmethod
    async def _get_pool():
        from metadata_db import get_metadata_pool
        pool = await get_metadata_pool()
        if not pool:
            raise RuntimeError("No metadata database connection available for index advisor")
        return pool

    @staticmethod
    def _resolve_tenant(tenant_id: Optional[str] = None) -> str:
        return tenant_id or TenantContext.get_tenant_id_or_default()
    
    @staticmethod
    async def analyze_unused_indexes(connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze unused indexes from pg_stat_user_indexes.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            List of unused index recommendations
        """
        try:
            config = configure_ssl(connection_config)
            conn = await asyncpg.connect(**config)

            # Check stats freshness — warn if reset recently
            stats_warning = None
            try:
                stats_reset = await conn.fetchval("""
                    SELECT stats_reset FROM pg_stat_database
                    WHERE datname = current_database()
                """)
                if stats_reset:
                    reset_age = datetime.utcnow() - stats_reset.replace(tzinfo=None)
                    if reset_age < timedelta(days=7):
                        stats_warning = (
                            f"Statistics were reset {reset_age.days} day(s) ago. "
                            f"Index usage data may be incomplete. "
                            f"Wait 1-2 weeks for reliable recommendations."
                        )
                        logger.warning(stats_warning)
            except Exception as e:
                logger.debug(f"Could not check stats_reset: {e}")

            # Query for unused indexes (idx_scan = 0) with catalog metadata
            query = """
                SELECT
                    sui.schemaname as schema_name,
                    sui.relname as table_name,
                    sui.indexrelname as index_name,
                    pg_size_pretty(pg_relation_size(sui.indexrelid)) as size_pretty,
                    pg_relation_size(sui.indexrelid) as size_bytes,
                    sui.idx_scan,
                    sui.idx_tup_read,
                    sui.idx_tup_fetch,
                    i.indisprimary,
                    i.indisunique
                FROM pg_stat_user_indexes sui
                JOIN pg_index i ON i.indexrelid = sui.indexrelid
                WHERE sui.idx_scan = 0
                ORDER BY pg_relation_size(sui.indexrelid) DESC
            """
            
            rows = await conn.fetch(query)
            await conn.close()
            
            recommendations = []
            for row in rows:
                # Since we can't determine exact last use from pg_stat_user_indexes,
                # we'll use idx_scan = 0 as the indicator
                days_unused = 0  # Unknown exact days, but we know idx_scan = 0
                
                # Calculate estimated savings
                estimated_savings_mb = row['size_bytes'] / (1024 * 1024)
                
                # Detect index type from pg_index catalog flags (not name heuristics)
                index_name = row['index_name']
                is_primary_key = row['indisprimary']
                is_unique = row['indisunique'] and not row['indisprimary']
                is_foreign_key = False  # PG doesn't auto-create FK indexes; not reliably detectable
                
                # Categorize safety level
                if is_primary_key:
                    safety_level = "critical"
                    reason = "Primary key index - required for data integrity and table structure. DO NOT DROP."
                    risk_level = "critical"
                elif is_unique:
                    safety_level = "critical"
                    reason = "Unique constraint index - enforces data uniqueness. Dropping will remove the constraint. Review carefully."
                    risk_level = "high"
                elif is_foreign_key:
                    safety_level = "needs_review"
                    reason = "Foreign key index - may be required for referential integrity. Review foreign key relationships before dropping."
                    risk_level = "high"
                else:
                    # Regular index - safe to drop if truly unused
                    safety_level = "safe"
                    if estimated_savings_mb > 100:
                        reason = f"Unused regular index (0 scans). Large size ({row['size_pretty']}) - good candidate for removal to save space."
                        risk_level = "low"
                    elif estimated_savings_mb > 10:
                        reason = f"Unused regular index (0 scans). Medium size ({row['size_pretty']}) - can be dropped to save space."
                        risk_level = "low"
                    else:
                        reason = f"Unused regular index (0 scans). Small size ({row['size_pretty']}) - minimal impact but can be cleaned up."
                        risk_level = "low"
                
                # Generate SQL fix
                sql_fix = f"DROP INDEX {row['schema_name']}.{row['index_name']};"
                
                recommendations.append({
                    'index_name': row['index_name'],
                    'table_name': row['table_name'],
                    'schema_name': row['schema_name'],
                    'size_bytes': row['size_bytes'],
                    'size_pretty': row['size_pretty'],
                    'idx_scan': row['idx_scan'],
                    'idx_tup_read': row['idx_tup_read'],
                    'idx_tup_fetch': row['idx_tup_fetch'],
                    'last_used': None,  # Not available from pg_stat_user_indexes
                    'days_unused': days_unused,
                    'estimated_savings_mb': round(estimated_savings_mb, 2),
                    'risk_level': risk_level,
                    'safety_level': safety_level,
                    'reason': reason,
                    'recommendation_type': 'drop',
                    'sql_fix': sql_fix,
                    'stats_warning': stats_warning,
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to analyze unused indexes: {e}")
            return []
    
    @staticmethod
    async def analyze_redundant_indexes(connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze potentially redundant indexes.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            List of redundant index recommendations
        """
        try:
            config = configure_ssl(connection_config)
            conn = await asyncpg.connect(**config)

            # Left-prefix redundancy: index (a) is redundant if (a, b) exists on same table
            prefix_query = """
                WITH idx_cols AS (
                    SELECT
                        n.nspname AS schema_name,
                        t.relname AS table_name,
                        i.relname AS index_name,
                        ix.indexrelid,
                        ix.indkey::int[] AS key_cols,
                        array_length(ix.indkey, 1) AS ncols,
                        pg_relation_size(ix.indexrelid) AS size_bytes,
                        pg_size_pretty(pg_relation_size(ix.indexrelid)) AS size_pretty,
                        COALESCE(s.idx_scan, 0) AS idx_scan,
                        COALESCE(s.idx_tup_read, 0) AS idx_tup_read,
                        COALESCE(s.idx_tup_fetch, 0) AS idx_tup_fetch,
                        ix.indisunique,
                        ix.indisprimary
                    FROM pg_index ix
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_class t ON t.oid = ix.indrelid
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    LEFT JOIN pg_stat_user_indexes s ON s.indexrelid = ix.indexrelid
                    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                      AND NOT ix.indisprimary
                )
                SELECT
                    a.schema_name, a.table_name, a.index_name,
                    a.size_pretty, a.size_bytes, a.idx_scan,
                    a.idx_tup_read, a.idx_tup_fetch,
                    b.index_name AS covered_by
                FROM idx_cols a
                JOIN idx_cols b ON a.table_name = b.table_name
                    AND a.schema_name = b.schema_name
                    AND a.indexrelid != b.indexrelid
                    AND a.ncols < b.ncols
                    AND a.key_cols = b.key_cols[1:a.ncols]
                WHERE NOT a.indisunique
                ORDER BY a.size_bytes DESC
                LIMIT 20
            """

            rows = await conn.fetch(prefix_query)
            await conn.close()

            recommendations = []
            for row in rows:
                estimated_savings_mb = row['size_bytes'] / (1024 * 1024)

                risk_level = "low" if row['idx_scan'] == 0 else ("high" if row['idx_scan'] > 5 else "medium")
                sql_fix = f"DROP INDEX {row['schema_name']}.{row['index_name']};"

                recommendations.append({
                    'index_name': row['index_name'],
                    'table_name': row['table_name'],
                    'schema_name': row['schema_name'],
                    'size_bytes': row['size_bytes'],
                    'size_pretty': row['size_pretty'],
                    'idx_scan': row['idx_scan'],
                    'idx_tup_read': row['idx_tup_read'],
                    'idx_tup_fetch': row['idx_tup_fetch'],
                    'last_used': None,
                    'days_unused': 0,
                    'estimated_savings_mb': round(estimated_savings_mb, 2),
                    'risk_level': risk_level,
                    'safety_level': 'safe',
                    'reason': f"Left-prefix redundant: columns are a prefix of {row['covered_by']}. Safe to drop.",
                    'recommendation_type': 'redundant',
                    'sql_fix': sql_fix,
                    'covered_by': row['covered_by'],
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to analyze redundant indexes: {e}")
            return []
    
    @classmethod
    async def store_index_recommendations(
        cls,
        recommendations: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> List[str]:
        if not recommendations:
            return []

        tenant = cls._resolve_tenant(tenant_id)
        pool = await cls._get_pool()
        stored_ids: List[str] = []
        created_at = datetime.utcnow()

        async with pool.acquire() as conn:
            for rec in recommendations:
                rec_id = rec.get('id') or str(uuid.uuid4())
                stored_ids.append(rec_id)
                await conn.execute(
                    """
                    INSERT INTO optischema.index_recommendations (
                        id,
                        tenant_id,
                        index_name,
                        table_name,
                        schema_name,
                        size_bytes,
                        size_pretty,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        last_used,
                        days_unused,
                        estimated_savings_mb,
                        risk_level,
                        safety_level,
                        reason,
                        recommendation_type,
                        sql_fix,
                        created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12, $13,
                        $14, $15, $16, $17, $18, $19
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        size_bytes = EXCLUDED.size_bytes,
                        size_pretty = EXCLUDED.size_pretty,
                        idx_scan = EXCLUDED.idx_scan,
                        idx_tup_read = EXCLUDED.idx_tup_read,
                        idx_tup_fetch = EXCLUDED.idx_tup_fetch,
                        last_used = EXCLUDED.last_used,
                        days_unused = EXCLUDED.days_unused,
                        estimated_savings_mb = EXCLUDED.estimated_savings_mb,
                        risk_level = EXCLUDED.risk_level,
                        safety_level = EXCLUDED.safety_level,
                        reason = EXCLUDED.reason,
                        recommendation_type = EXCLUDED.recommendation_type,
                        sql_fix = EXCLUDED.sql_fix,
                        created_at = EXCLUDED.created_at
                    """,
                    rec_id,
                    tenant,
                    rec['index_name'],
                    rec['table_name'],
                    rec['schema_name'],
                    rec['size_bytes'],
                    rec['size_pretty'],
                    rec['idx_scan'],
                    rec['idx_tup_read'],
                    rec['idx_tup_fetch'],
                    rec.get('last_used'),
                    rec['days_unused'],
                    rec['estimated_savings_mb'],
                    rec['risk_level'],
                    rec.get('safety_level', 'needs_review'),
                    rec.get('reason', 'No reason provided'),
                    rec['recommendation_type'],
                    rec.get('sql_fix'),
                    rec.get('created_at', created_at),
                )
        logger.info("Stored %s index recommendations for tenant %s", len(stored_ids), tenant)
        return stored_ids

    @classmethod
    async def get_index_recommendations(
        cls,
        recommendation_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        tenant = cls._resolve_tenant(tenant_id)
        pool = await cls._get_pool()

        query_parts = [
            "SELECT * FROM optischema.index_recommendations WHERE tenant_id = $1"
        ]
        params: List[Any] = [tenant]

        if recommendation_type:
            params.append(recommendation_type)
            query_parts.append(f"AND recommendation_type = ${len(params)}")
        if risk_level:
            params.append(risk_level)
            query_parts.append(f"AND risk_level = ${len(params)}")

        params.extend([limit, offset])
        query_parts.append(f"ORDER BY created_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}")

        async with pool.acquire() as conn:
            rows = await conn.fetch("\n".join(query_parts), *params)

        return [dict(row) for row in rows]

    @classmethod
    async def get_index_recommendation_summary(
        cls,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tenant = cls._resolve_tenant(tenant_id)
        pool = await cls._get_pool()

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM optischema.index_recommendations WHERE tenant_id = $1",
                tenant,
            )
            type_rows = await conn.fetch(
                """
                SELECT recommendation_type, COUNT(*)
                FROM optischema.index_recommendations
                WHERE tenant_id = $1
                GROUP BY recommendation_type
                """,
                tenant,
            )
            risk_rows = await conn.fetch(
                """
                SELECT risk_level, COUNT(*)
                FROM optischema.index_recommendations
                WHERE tenant_id = $1
                GROUP BY risk_level
                """,
                tenant,
            )
            savings = await conn.fetchval(
                """
                SELECT SUM(estimated_savings_mb)
                FROM optischema.index_recommendations
                WHERE tenant_id = $1
                """,
                tenant,
            )
            recent = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM optischema.index_recommendations
                WHERE tenant_id = $1 AND created_at >= NOW() - INTERVAL '1 day'
                """,
                tenant,
            )

        return {
            "total_recommendations": total or 0,
            "recommendations_by_type": {row[0]: row[1] for row in type_rows},
            "recommendations_by_risk": {row[0]: row[1] for row in risk_rows},
            "total_potential_savings_mb": round(savings or 0, 2),
            "recent_recommendations_24h": recent or 0,
        }

    @classmethod
    async def delete_recommendation(cls, recommendation_id: str, tenant_id: Optional[str] = None) -> bool:
        """Delete a specific recommendation."""
        tenant = cls._resolve_tenant(tenant_id)
        pool = await cls._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM optischema.index_recommendations WHERE tenant_id = $1 AND id = $2",
                tenant,
                recommendation_id,
            )
        deleted = result.startswith("DELETE") and result.split()[-1] != "0"
        if deleted:
            logger.info("Deleted index recommendation %s for tenant %s", recommendation_id, tenant)
        return deleted
    
    @staticmethod
    async def get_database_index_stats(connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get database index statistics to understand what indexes exist.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            Dictionary with index statistics
        """
        try:
            config = configure_ssl(connection_config)
            conn = await asyncpg.connect(**config)

            # Get total number of user indexes
            total_indexes_query = """
                SELECT COUNT(*) as total_indexes
                FROM pg_stat_user_indexes
            """
            
            # Get indexes by usage
            usage_stats_query = """
                SELECT 
                    CASE 
                        WHEN idx_scan = 0 THEN 'unused'
                        WHEN idx_scan < 10 THEN 'low_usage'
                        WHEN idx_scan < 100 THEN 'medium_usage'
                        ELSE 'high_usage'
                    END as usage_category,
                    COUNT(*) as count,
                    SUM(pg_relation_size(indexrelid)) as total_size_bytes
                FROM pg_stat_user_indexes
                GROUP BY 
                    CASE 
                        WHEN idx_scan = 0 THEN 'unused'
                        WHEN idx_scan < 10 THEN 'low_usage'
                        WHEN idx_scan < 100 THEN 'medium_usage'
                        ELSE 'high_usage'
                    END
                ORDER BY usage_category
            """
            
            # Get largest indexes
            largest_indexes_query = """
                SELECT 
                    schemaname as schema_name,
                    relname as table_name,
                    indexrelname as index_name,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size_pretty,
                    pg_relation_size(indexrelid) as size_bytes,
                    idx_scan
                FROM pg_stat_user_indexes
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 10
            """
            
            total_result = await conn.fetchrow(total_indexes_query)
            usage_results = await conn.fetch(usage_stats_query)
            largest_results = await conn.fetch(largest_indexes_query)
            
            await conn.close()
            
            # Process usage stats
            usage_stats = {}
            for row in usage_results:
                usage_stats[row['usage_category']] = {
                    'count': row['count'],
                    'total_size_mb': round(row['total_size_bytes'] / (1024 * 1024), 2)
                }
            
            # Process largest indexes
            largest_indexes = []
            for row in largest_results:
                largest_indexes.append({
                    'schema_name': row['schema_name'],
                    'table_name': row['table_name'],
                    'index_name': row['index_name'],
                    'size_pretty': row['size_pretty'],
                    'size_bytes': row['size_bytes'],
                    'idx_scan': row['idx_scan']
                })
            
            return {
                "total_indexes": total_result['total_indexes'],
                "usage_stats": usage_stats,
                "largest_indexes": largest_indexes
            }
            
        except Exception as e:
            logger.error(f"Failed to get database index stats: {e}")
            return {
                "total_indexes": 0,
                "usage_stats": {},
                "largest_indexes": [],
                "error": str(e)
            }

    @classmethod
    async def run_full_analysis(
        cls,
        connection_config: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run full index analysis and store recommendations.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            Analysis results summary
        """
        tenant = cls._resolve_tenant(tenant_id)

        try:
            # Get database index statistics first
            index_stats = await IndexAdvisorService.get_database_index_stats(connection_config)
            
            # Analyze unused indexes
            unused_indexes = await IndexAdvisorService.analyze_unused_indexes(connection_config)
            
            # Analyze redundant indexes
            redundant_indexes = await IndexAdvisorService.analyze_redundant_indexes(connection_config)
            
            # Combine all recommendations
            all_recommendations = unused_indexes + redundant_indexes
            
            # Store recommendations
            if all_recommendations:
                recommendation_ids = await IndexAdvisorService.store_index_recommendations(
                    all_recommendations,
                    tenant_id=tenant
                )
            else:
                recommendation_ids = []
            
            # Calculate summary
            total_savings = sum(rec['estimated_savings_mb'] for rec in all_recommendations)
            
            return {
                "success": True,
                "total_recommendations": len(all_recommendations),
                "unused_indexes": len(unused_indexes),
                "redundant_indexes": len(redundant_indexes),
                "total_potential_savings_mb": round(total_savings, 2),
                "recommendation_ids": recommendation_ids,
                "analyzed_at": datetime.utcnow().isoformat(),
                "database_stats": index_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to run full index analysis: {e}")
            return {
                "success": False,
                "error": str(e)
            } 

    @staticmethod
    async def list_present_indexes(connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        List current indexes with size and usage for the given connection.
        """
        try:
            config = configure_ssl(connection_config)
            conn = await asyncpg.connect(**config)

            # Query to fetch present indexes with size and usage
            query = """
                WITH indexed AS (
                  SELECT 
                    i.schemaname AS schema_name,
                    i.tablename AS table_name,
                    i.indexname AS index_name,
                    i.indexdef AS index_definition
                  FROM pg_indexes i
                  WHERE i.schemaname NOT IN ('pg_catalog', 'information_schema')
                ), sizes AS (
                  SELECT 
                    c.relname AS index_name,
                    pg_relation_size(c.oid) AS size_bytes,
                    pg_size_pretty(pg_relation_size(c.oid)) AS size_pretty
                  FROM pg_class c
                  WHERE c.relkind = 'i'
                )
                SELECT 
                  idx.schema_name,
                  idx.table_name,
                  idx.index_name,
                  idx.index_definition,
                  COALESCE(sz.size_bytes, 0) AS size_bytes,
                  COALESCE(sz.size_pretty, '0 bytes') AS size_pretty,
                  COALESCE(psui.idx_scan, 0) AS idx_scan
                FROM indexed idx
                LEFT JOIN sizes sz ON sz.index_name = idx.index_name
                LEFT JOIN pg_stat_user_indexes psui 
                  ON psui.schemaname = idx.schema_name AND psui.indexrelname = idx.index_name
                ORDER BY sz.size_bytes DESC, idx.schema_name, idx.table_name, idx.index_name
                LIMIT 1000
            """

            rows = await conn.fetch(query)
            await conn.close()

            result: List[Dict[str, Any]] = []
            for row in rows:
                result.append({
                    'schema_name': row['schema_name'],
                    'table_name': row['table_name'],
                    'index_name': row['index_name'],
                    'index_definition': row['index_definition'],
                    'size_bytes': row['size_bytes'],
                    'size_pretty': row['size_pretty'],
                    'idx_scan': row['idx_scan'],
                })
            return result
        except Exception as e:
            logger.error(f"Failed to list present indexes: {e}")
            return []
