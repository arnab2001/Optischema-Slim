"""
Health Scan Service for OptiSchema Slim.
Performs comprehensive database health checks including bloat, indexes, and configuration.

Current implementation uses deterministic rules to detect:
- Table bloat based on dead tuple ratios
- Unused indexes based on scan counts
- Configuration issues based on known thresholds

Future enhancement: Add optional AI-powered global analysis that:
- Correlates health findings with query patterns
- Suggests optimization strategies across multiple tables
- Prioritizes issues by business impact
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from connection_manager import connection_manager

logger = logging.getLogger(__name__)


class HealthScanService:
    """Service for performing database health scans."""
    
    async def perform_scan(self) -> Dict[str, Any]:
        """
        Perform a comprehensive database health scan.
        
        Returns:
            Dictionary containing scan results with bloat, index, and config issues
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {
                "error": "No database connection",
                "scan_timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            async with pool.acquire() as conn:
                # Run all checks in parallel where possible
                table_bloat = await self._check_table_bloat(conn)
                index_bloat = await self._check_index_bloat(conn)
                config_issues = await self._check_configuration(conn)
                
                # Calculate overall health score (0-100)
                health_score = self._calculate_health_score(table_bloat, index_bloat, config_issues)
                
                return {
                    "scan_timestamp": datetime.utcnow().isoformat(),
                    "health_score": health_score,
                    "table_bloat": table_bloat,
                    "index_bloat": index_bloat,
                    "config_issues": config_issues,
                    "summary": {
                        "total_bloated_tables": len(table_bloat.get("issues", [])),
                        "total_unused_indexes": len(index_bloat.get("unused_indexes", [])),
                        "total_config_issues": len(config_issues.get("issues", []))
                    }
                }
        except Exception as e:
            logger.error(f"Error performing health scan: {e}")
            return {
                "error": str(e),
                "scan_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_table_bloat(self, conn) -> Dict[str, Any]:
        """Check for table bloat issues."""
        try:
            rows = await conn.fetch("""
                SELECT 
                    schemaname,
                    relname AS tablename,
                    n_live_tup,
                    n_dead_tup,
                    last_autovacuum,
                    last_vacuum,
                    CASE 
                        WHEN (n_live_tup + n_dead_tup) > 0 
                        THEN (n_dead_tup::float / (n_live_tup + n_dead_tup)::float) * 100
                        ELSE 0 
                    END AS dead_ratio
                FROM pg_stat_user_tables
                WHERE n_dead_tup > 0
                ORDER BY dead_ratio DESC
            """)
            
            issues = []
            for row in rows:
                dead_ratio = row["dead_ratio"] or 0
                n_live_tup = row["n_live_tup"] or 0
                n_dead_tup = row["n_dead_tup"] or 0
                last_autovacuum = row["last_autovacuum"]
                
                # Flag tables with >20% dead tuples
                if dead_ratio > 20.0:
                    # Check if autovacuum is overdue (>3 days)
                    vacuum_overdue = False
                    if last_autovacuum:
                        # Handle timezone-aware and naive datetimes
                        if last_autovacuum.tzinfo:
                            now = datetime.now(last_autovacuum.tzinfo)
                        else:
                            now = datetime.utcnow()
                        days_since_vacuum = (now - last_autovacuum).days
                        vacuum_overdue = days_since_vacuum > 3
                    else:
                        vacuum_overdue = True  # Never vacuumed
                    
                    severity = "high" if dead_ratio > 50.0 or vacuum_overdue else "medium"
                    
                    issues.append({
                        "schema": row["schemaname"],
                        "table": row["tablename"],
                        "dead_ratio": round(dead_ratio, 2),
                        "live_tuples": n_live_tup,
                        "dead_tuples": n_dead_tup,
                        "last_autovacuum": last_autovacuum.isoformat() if last_autovacuum else None,
                        "vacuum_overdue": vacuum_overdue,
                        "severity": severity,
                        "recommendation": "Run VACUUM ANALYZE" if not vacuum_overdue else "Run VACUUM ANALYZE (autovacuum may be disabled or failing)"
                    })
            
            return {
                "checked": True,
                "issues": issues,
                "total_tables_checked": len(rows) if rows else 0
            }
        except Exception as e:
            logger.error(f"Error checking table bloat: {e}")
            return {
                "checked": False,
                "error": str(e),
                "issues": []
            }
    
    async def _check_index_bloat(self, conn) -> Dict[str, Any]:
        """Check for unused or redundant indexes."""
        try:
            # Get unused indexes (idx_scan = 0)
            unused_indexes = await conn.fetch("""
                SELECT 
                    schemaname,
                    relname AS tablename,
                    indexrelname AS indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                    pg_relation_size(indexrelid) AS index_size_bytes
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                  AND schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            
            # Get index creation time (approximate from pg_class)
            unused_list = []
            for idx in unused_indexes:
                # Check if index is relatively new (<7 days) - might be unused temporarily
                # We'll flag it but with lower severity
                unused_list.append({
                    "schema": idx["schemaname"],
                    "table": idx["tablename"],
                    "index": idx["indexname"],
                    "scans": idx["idx_scan"],
                    "tuples_read": idx["idx_tup_read"],
                    "tuples_fetched": idx["idx_tup_fetch"],
                    "size": idx["index_size"],
                    "size_bytes": idx["index_size_bytes"],
                    "severity": "low",  # Could be a new index or rarely used
                    "recommendation": "Monitor for a few more days before dropping. Verify index is not needed for unique constraints or foreign keys."
                })
            
            return {
                "checked": True,
                "unused_indexes": unused_list,
                "total_unused": len(unused_list)
            }
        except Exception as e:
            logger.error(f"Error checking index bloat: {e}")
            return {
                "checked": False,
                "error": str(e),
                "unused_indexes": []
            }
    
    async def _check_configuration(self, conn) -> Dict[str, Any]:
        """Check for suboptimal PostgreSQL configuration."""
        try:
            # Get critical settings
            settings = await conn.fetch("""
                SELECT name, setting, unit, context
                FROM pg_settings
                WHERE name IN (
                    'shared_buffers',
                    'effective_cache_size',
                    'work_mem',
                    'checkpoint_completion_target',
                    'max_wal_size',
                    'checkpoint_timeout',
                    'maintenance_work_mem',
                    'random_page_cost'
                )
            """)
            
            settings_dict = {s["name"]: s for s in settings}
            issues = []
            
            # Check shared_buffers (should be ~25% of RAM, but we can't know RAM, so check if reasonable)
            if "shared_buffers" in settings_dict:
                shared_buffers = settings_dict["shared_buffers"]
                # Convert to bytes for comparison
                value_str = shared_buffers["setting"]
                unit = shared_buffers.get("unit", "")
                # Basic check: if less than 128MB, it's likely too low
                if unit == "8kB":
                    value_bytes = int(value_str) * 8192
                    if value_bytes < 128 * 1024 * 1024:  # Less than 128MB
                        issues.append({
                            "setting": "shared_buffers",
                            "current_value": f"{value_str} {unit}",
                            "severity": "medium",
                            "issue": "shared_buffers is very low (<128MB)",
                            "recommendation": "Consider increasing shared_buffers to 25% of available RAM (typically 1-4GB for small to medium databases)"
                        })
            
            # Check checkpoint_completion_target (should be 0.9)
            if "checkpoint_completion_target" in settings_dict:
                target = float(settings_dict["checkpoint_completion_target"]["setting"])
                if target < 0.7:
                    issues.append({
                        "setting": "checkpoint_completion_target",
                        "current_value": str(target),
                        "severity": "medium",
                        "issue": "checkpoint_completion_target is too low",
                        "recommendation": "Set checkpoint_completion_target to 0.9 to spread checkpoint I/O over time"
                    })
            
            # Check work_mem (if very low, could cause disk sorts)
            if "work_mem" in settings_dict:
                work_mem = settings_dict["work_mem"]
                value_str = work_mem["setting"]
                unit = work_mem.get("unit", "")
                if unit == "kB":
                    value_kb = int(value_str)
                    if value_kb < 4096:  # Less than 4MB
                        issues.append({
                            "setting": "work_mem",
                            "current_value": f"{value_str} {unit}",
                            "severity": "low",
                            "issue": "work_mem is quite low (<4MB)",
                            "recommendation": "Consider increasing work_mem if you see many disk-based sorts in EXPLAIN plans"
                        })
            
            return {
                "checked": True,
                "issues": issues,
                "total_settings_checked": len(settings)
            }
        except Exception as e:
            logger.error(f"Error checking configuration: {e}")
            return {
                "checked": False,
                "error": str(e),
                "issues": []
            }
    
    def _calculate_health_score(self, table_bloat: Dict, index_bloat: Dict, config_issues: Dict) -> int:
        """Calculate overall health score (0-100)."""
        score = 100
        
        # Deduct points for table bloat
        bloat_issues = table_bloat.get("issues", [])
        for issue in bloat_issues:
            if issue.get("severity") == "high":
                score -= 10
            else:
                score -= 5
        
        # Deduct points for unused indexes (less critical)
        unused_count = len(index_bloat.get("unused_indexes", []))
        score -= min(unused_count * 2, 20)  # Max 20 points deduction
        
        # Deduct points for config issues
        config_issue_list = config_issues.get("issues", [])
        for issue in config_issue_list:
            if issue.get("severity") == "high":
                score -= 5
            else:
                score -= 2
        
        return max(0, min(100, score))


# Global instance
health_scan_service = HealthScanService()
