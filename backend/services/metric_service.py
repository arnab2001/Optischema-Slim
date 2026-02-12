"""
Metric Service for OptiSchema Slim.
Fetches query metrics from pg_stat_statements.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from connection_manager import connection_manager

logger = logging.getLogger(__name__)


class MetricService:
    def _build_query_metrics_sql(self, include_system_queries: bool = False) -> tuple[str, str, str]:
        """
        Build version-aware SQL for query metrics.
        Returns tuple of (select_clause, where_clause, order_by_expr).
        """
        pg_version = connection_manager.get_pg_version()
        # Default to OLD (PG12) syntax when version is unknown — safer than crashing
        use_new_columns = pg_version is not None and pg_version >= 130000
        
        # Build SELECT clause with version-aware timing columns
        if use_new_columns:  # PostgreSQL 13+ renamed timing columns and added plan time
            total_time_expr = "(total_exec_time + COALESCE(total_plan_time, 0))"
            mean_col = "mean_exec_time"
            stddev_col = "stddev_exec_time"
            min_col = "min_exec_time"
            max_col = "max_exec_time"
            order_by_expr = "(total_exec_time + COALESCE(total_plan_time, 0))"
        else:  # PostgreSQL < 13 uses the older column names
            total_time_expr = "total_time"
            mean_col = "mean_time"
            stddev_col = "stddev_time"
            min_col = "min_time"
            max_col = "max_time"
            order_by_expr = "total_time"
        
        select_clause = f"""
            CAST(queryid AS TEXT) AS queryid,
            query,
            {total_time_expr}::BIGINT AS total_time,
            calls::BIGINT,
            {mean_col}::FLOAT8 AS mean_time,
            {stddev_col}::FLOAT8 AS stddev_time,
            {min_col}::BIGINT AS min_time,
            {max_col}::BIGINT AS max_time,
            rows::BIGINT,
            shared_blks_hit::BIGINT,
            shared_blks_read::BIGINT,
            shared_blks_written::BIGINT,
            shared_blks_dirtied::BIGINT,
            temp_blks_read::BIGINT,
            temp_blks_written::BIGINT,
            blk_read_time::FLOAT8,
            blk_write_time::FLOAT8
        """
        
        # Build WHERE clause with conditional filtering
        where_conditions = ["1=1"]
        if not include_system_queries:
            where_conditions.extend([
                "AND query NOT ILIKE 'EXPLAIN%'",
                "AND query NOT ILIKE 'DEALLOCATE%'",
                "AND query NOT ILIKE 'SET %'",
                "AND query NOT ILIKE 'SHOW %'",
                "AND query NOT ILIKE 'BEGIN%'",
                "AND query NOT ILIKE 'COMMIT%'",
                "AND query NOT ILIKE 'ROLLBACK%'",
                "AND query NOT ILIKE 'SAVEPOINT%'",
                "AND query NOT ILIKE 'FETCH %'",
                "AND query NOT ILIKE 'MOVE %'",
                "AND query NOT ILIKE 'DECLARE %'",
                "AND query NOT ILIKE 'SELECT%FROM pg\\_%'",
                "AND query NOT ILIKE 'SELECT%FROM information_schema.%'"
            ])
        
        where_clause = " ".join(where_conditions)
        
        return select_clause, where_clause, order_by_expr
    
    async def fetch_query_metrics(self, sample_size: int = 50, include_system_queries: bool = False) -> Dict[str, Any]:
        """
        Fetch query metrics from pg_stat_statements.
        Args:
            sample_size: Number of top queries to fetch (default 50)
        Returns:
            Dict with 'metrics' (list) and 'total_count' (int)
        """
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No active database connection")
            return {"metrics": [], "total_count": 0}
        
        # Clamp sample_size to sane limits
        sample_size = max(10, min(sample_size, 500))
        
        try:
            async with pool.acquire() as conn:
                # Check if pg_stat_statements is enabled
                enabled = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension 
                        WHERE extname = 'pg_stat_statements'
                    )
                """)
                
                if not enabled:
                    logger.warning("pg_stat_statements is not enabled")
                    return {"metrics": [], "total_count": 0}
                
                # Build version-aware SQL
                select_clause, where_clause, order_by_expr = self._build_query_metrics_sql(include_system_queries)
                
                # Get total count first
                count_query = f"SELECT COUNT(*) FROM pg_stat_statements WHERE {where_clause}"
                total_count = await conn.fetchval(count_query) or 0
                
                # Fetch sampled metrics
                query = f"""
                    SELECT
                        {select_clause}
                    FROM pg_stat_statements
                    WHERE {where_clause}
                    ORDER BY {order_by_expr} DESC
                    LIMIT {sample_size}
                """
                rows = await conn.fetch(query)
                
                return {
                    "metrics": [dict(row) for row in rows],
                    "total_count": total_count
                }
                
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return {"metrics": [], "total_count": 0}

    async def fetch_vitals(self) -> Dict[str, Any]:
        """
        Fetch database vitals: QPS, Cache Hit Ratio, Active Connections.
        Returns metrics with status indicators (ok, insufficient_data, disabled).
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {
                "qps": {"value": 0.0, "status": "disabled"},
                "cache_hit_ratio": {"value": None, "status": "disabled"},
                "active_connections": {"value": 0, "status": "disabled"},
                "max_connections": {"value": 100, "status": "ok"},
                "error": "No database connection"
            }
        
        try:
            async with pool.acquire() as conn:
                # Get cache hit ratio from pg_stat_database
                cache_hit = await conn.fetchrow("""
                    SELECT 
                        blks_hit,
                        blks_read,
                        CASE WHEN (blks_hit + blks_read) > 0 
                        THEN (blks_hit::float / (blks_hit + blks_read)::float) * 100 
                        ELSE NULL END AS cache_hit_ratio
                    FROM pg_stat_database
                    WHERE datname = current_database()
                """)
                
                # Get active connections
                connections = await conn.fetchrow("""
                    SELECT 
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') AS active,
                        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_conn
                """)
                
                # Simple QPS estimate: total calls / uptime in seconds
                # Note: pg_stat_statements_info only exists in PG 14+
                qps_value = 0.0
                qps_status = "ok"
                
                # Check if pg_stat_statements extension exists and is enabled
                try:
                    pg_stat_enabled = await conn.fetchval("""
                        SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')
                    """)
                    
                    if not pg_stat_enabled:
                        qps_status = "disabled"
                    else:
                        # Extension is enabled, try to calculate QPS
                        try:
                            qps_result = await conn.fetchval("""
                                SELECT COALESCE(SUM(calls), 0)::float 
                                FROM pg_stat_statements
                            """) or 0
                            
                            # Always calculate QPS if we have a result, even if it's 0
                            # Prefer time since stats reset if available (PG14+)
                            stats_reset = None
                            try:
                                stats_reset = await conn.fetchval("SELECT stats_reset FROM pg_stat_statements_info")
                            except Exception:
                                stats_reset = None
                            
                            # Calculate time window
                            time_window = 1.0  # Default to 1 second to avoid division by zero
                            if stats_reset:
                                time_window = await conn.fetchval("SELECT EXTRACT(EPOCH FROM (now() - $1))", stats_reset) or 1.0
                            else:
                                time_window = await conn.fetchval("""
                                    SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))
                                    FROM pg_stat_activity LIMIT 1
                                """) or 1.0
                            
                            # Calculate QPS from pg_stat_statements
                            if qps_result > 0 and time_window > 0:
                                qps_value = round(qps_result / max(time_window, 1), 4)  # More precision
                            
                            # Fallback to transaction rate if pg_stat_statements has no calls or very low QPS
                            if qps_value == 0:
                                tx_calls = await conn.fetchrow("""
                                    SELECT 
                                        COALESCE(xact_commit, 0)::float + COALESCE(xact_rollback, 0)::float AS tx_count,
                                        stats_reset
                                    FROM pg_stat_database
                                    WHERE datname = current_database()
                                """)
                                if tx_calls and tx_calls["tx_count"] > 0:
                                    if tx_calls["stats_reset"]:
                                        tx_window = await conn.fetchval(
                                            "SELECT EXTRACT(EPOCH FROM (now() - $1))",
                                            tx_calls["stats_reset"]
                                        ) or 1
                                    else:
                                        tx_window = await conn.fetchval("""
                                            SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))
                                            FROM pg_stat_activity LIMIT 1
                                        """) or 1
                                    qps_value = round(tx_calls["tx_count"] / max(tx_window, 1), 2)
                        except Exception as e:
                            # Extension is enabled but querying stats failed - keep status as ok, value stays 0.0
                            logger.warning(f"Could not query pg_stat_statements (extension enabled): {e}")
                            # qps_value already 0.0, qps_status already "ok"
                except Exception as e:
                    # Extension check itself failed
                    logger.warning(f"Could not check pg_stat_statements extension: {e}")
                    qps_status = "disabled"
                
                # Get WAL stats from pg_stat_bgwriter
                wal_stats = {}
                try:
                    bgwriter = await conn.fetchrow("""
                        SELECT 
                            buffers_checkpoint,
                            buffers_clean,
                            buffers_backend,
                            checkpoints_timed,
                            checkpoints_req,
                            checkpoint_write_time,
                            checkpoint_sync_time
                        FROM pg_stat_bgwriter
                    """)
                    if bgwriter:
                        total_checkpoints = bgwriter["checkpoints_timed"] + bgwriter["checkpoints_req"]
                        checkpoint_pressure = 0.0
                        if total_checkpoints > 0:
                            checkpoint_pressure = bgwriter["checkpoints_req"] / total_checkpoints
                        
                        wal_stats = {
                            "buffers_checkpoint": bgwriter["buffers_checkpoint"],
                            "buffers_clean": bgwriter["buffers_clean"],
                            "buffers_backend": bgwriter["buffers_backend"],
                            "checkpoints_timed": bgwriter["checkpoints_timed"],
                            "checkpoints_req": bgwriter["checkpoints_req"],
                            "checkpoint_write_time": bgwriter["checkpoint_write_time"],
                            "checkpoint_sync_time": bgwriter["checkpoint_sync_time"],
                            "checkpoint_pressure_ratio": round(checkpoint_pressure, 3)
                        }
                except Exception as e:
                    logger.warning(f"Could not fetch WAL stats: {e}")
                
                # Cache hit ratio with status indicator
                cache_ratio_value = None
                cache_ratio_status = "ok"
                cache_sample_size = 0
                
                if cache_hit:
                    hits = cache_hit.get("blks_hit") or 0
                    reads = cache_hit.get("blks_read") or 0
                    total_blocks = hits + reads
                    cache_sample_size = total_blocks
                    
                    # Check if we have sufficient data (threshold: 1000 total reads)
                    if total_blocks < 1000:
                        cache_ratio_status = "insufficient_data"
                    elif reads > 0 and cache_hit["cache_hit_ratio"] is not None:
                        cache_ratio_value = round(cache_hit["cache_hit_ratio"], 1)
                    else:
                        cache_ratio_status = "insufficient_data"

                return {
                    "qps": {"value": qps_value, "status": qps_status},
                    "cache_hit_ratio": {
                        "value": cache_ratio_value,
                        "status": cache_ratio_status,
                        "sample_size": cache_sample_size
                    },
                    "active_connections": {
                        "value": connections["active"] if connections else 0,
                        "status": "ok"
                    },
                    "max_connections": {
                        "value": connections["max_conn"] if connections else 100,
                        "status": "ok"
                    },
                    "wal_stats": wal_stats
                }
                
        except Exception as e:
            logger.error(f"Error fetching vitals: {e}")
            return {
                "qps": {"value": 0.0, "status": "disabled"},
                "cache_hit_ratio": {"value": None, "status": "disabled"},
                "active_connections": {"value": 0, "status": "disabled"},
                "max_connections": {"value": 100, "status": "ok"},
                "error": str(e)
            }

    async def fetch_db_info(self) -> Dict[str, Any]:
        """
        Fetch database information: version, extensions, size, etc.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection"}
        
        try:
            async with pool.acquire() as conn:
                # Get PostgreSQL version
                version = await conn.fetchval("SELECT version()")
                version_short = await conn.fetchval("SHOW server_version")
                
                # Get enabled extensions
                extensions = await conn.fetch("""
                    SELECT extname, extversion 
                    FROM pg_extension 
                    ORDER BY extname
                """)
                
                # Get database size
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                
                # Get database name
                db_name = await conn.fetchval("SELECT current_database()")
                
                # Get table count
                table_count = await conn.fetchval("""
                    SELECT count(*) FROM information_schema.tables 
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                """)
                
                # Get per-table row counts and sizes
                table_stats = []
                total_approximate_rows = 0
                try:
                    table_rows = await conn.fetch("""
                        SELECT 
                            n.nspname AS schemaname,
                            c.relname AS tablename,
                            COALESCE(c.reltuples::bigint, 0) AS approximate_rows,
                            pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
                            pg_total_relation_size(c.oid) AS total_size_bytes
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE c.relkind = 'r'
                          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                        ORDER BY c.reltuples DESC
                    """)
                    
                    for row in table_rows:
                        rows = row["approximate_rows"] or 0
                        total_approximate_rows += rows
                        table_stats.append({
                            "schema": row["schemaname"],
                            "table": row["tablename"],
                            "approximate_rows": rows,
                            "total_size": row["total_size"],
                            "total_size_bytes": row["total_size_bytes"]
                        })
                except Exception as e:
                    logger.warning(f"Could not fetch table row counts: {e}")
                
                # Check for key extensions
                ext_list = [r["extname"] for r in extensions]
                
                return {
                    "version": version_short,
                    "version_full": version,
                    "database_name": db_name,
                    "database_size": db_size,
                    "table_count": table_count,
                    "total_approximate_rows": total_approximate_rows,
                    "table_row_counts": table_stats,
                    "extensions": [{"name": r["extname"], "version": r["extversion"]} for r in extensions],
                    "has_pg_stat_statements": "pg_stat_statements" in ext_list,
                    "has_hypopg": "hypopg" in ext_list
                }
                
        except Exception as e:
            logger.error(f"Error fetching DB info: {e}")
            return {"error": str(e)}

    async def reset_stats(self) -> bool:
        """
        Reset pg_stat_statements statistics.
        Returns True if successful, False otherwise.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return False
            
        try:
            async with pool.acquire() as conn:
                # Check if extension exists first
                exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')")
                if not exists:
                    return False
                    
                await conn.execute("SELECT pg_stat_statements_reset()")
                return True
        except Exception as e:
            logger.error(f"Error resetting stats: {e}")
            return False

    async def fetch_single_query(self, queryid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single query's metrics by queryid.
        """
        pool = await connection_manager.get_pool()
        if not pool:
            return None
            
        try:
            async with pool.acquire() as conn:
                # Build version-aware SQL (always include system for direct lookup)
                select_clause, _, _ = self._build_query_metrics_sql(include_system_queries=True)
                
                query = f"""
                    SELECT {select_clause}
                    FROM pg_stat_statements
                    WHERE CAST(queryid AS TEXT) = $1
                    LIMIT 1
                """
                row = await conn.fetchrow(query, queryid)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching single query {queryid}: {e}")
            return None

metric_service = MetricService()
