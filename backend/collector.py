"""
Collector module for OptiSchema backend.
Fetches and aggregates query metrics from pg_stat_statements.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from db import get_pool
from connection_manager import connection_manager
from models import QueryMetrics
from config import settings
from utils import calculate_performance_score

# Global collector task reference
_collector_task: Optional[asyncio.Task] = None

# In-memory cache for collected metrics
metrics_cache: List[QueryMetrics] = []
last_updated: datetime = None

logger = logging.getLogger(__name__)

# Configuration for large dataset handling
MAX_QUERIES_DEFAULT = 50000  # Maximum queries to collect by default
SAMPLING_THRESHOLD = 100000  # Start sampling when this many queries exist
MIN_CALLS_FILTER = 1  # Only collect queries with at least this many calls (reduced for testing)
MIN_TIME_FILTER = 0.0  # Only collect queries with at least this mean time (ms) (reduced for testing)

PG_STAT_QUERY = """
SELECT
    md5(query) AS query_hash,
    query,
    total_exec_time::BIGINT AS total_time,
    calls::BIGINT,
    mean_exec_time::FLOAT8 AS mean_time,
    stddev_exec_time::FLOAT8 AS stddev_time,
    min_exec_time::BIGINT AS min_time,
    max_exec_time::BIGINT AS max_time,
    rows::BIGINT,
    shared_blks_hit::BIGINT,
    shared_blks_read::BIGINT,
    shared_blks_written::BIGINT,
    shared_blks_dirtied::BIGINT,
    temp_blks_read::BIGINT,
    temp_blks_written::BIGINT,
    blk_read_time::FLOAT8,
    blk_write_time::FLOAT8
FROM pg_stat_statements
WHERE 1=1
  -- Exclude obvious maintenance and system queries
  AND query NOT ILIKE 'EXPLAIN%'
  AND query NOT ILIKE 'DEALLOCATE%'
  AND query NOT ILIKE 'SET %'
  AND query NOT ILIKE 'SHOW %'
  AND query NOT ILIKE 'BEGIN%'
  AND query NOT ILIKE 'COMMIT%'
  AND query NOT ILIKE 'ROLLBACK%'
  AND query NOT ILIKE 'SAVEPOINT%'
  AND query NOT ILIKE 'FETCH %'
  AND query NOT ILIKE 'MOVE %'
  AND query NOT ILIKE 'DECLARE %'
  AND query NOT ILIKE '%query-cursor_%'
  -- Exclude pg_catalog/information_schema and RDS helper calls
  AND query NOT ILIKE 'SELECT%FROM pg\_%'
  AND query NOT ILIKE 'SELECT%FROM information_schema.%'
  AND query NOT ILIKE 'SELECT pg\_%(%'
  AND query NOT ILIKE 'SELECT%FROM pg_show_all_settings%'
  AND query NOT ILIKE '%pg_settings%'
  AND query NOT ILIKE 'SELECT rds\_%'
  -- Very small literal-only selects like SELECT $1
  AND NOT (query ~* '^\\s*SELECT\\s+\\$[0-9]+')
  -- Specific noisy statements
  AND query NOT ILIKE 'SET statement_timeout%'
  AND query NOT ILIKE 'SELECT pg_switch_wal%'
  AND calls >= $1
  AND mean_exec_time >= $2
ORDER BY total_exec_time DESC
LIMIT $3;
"""

async def fetch_pg_stat() -> List[QueryMetrics]:
    """Fetch query metrics from pg_stat_statements with smart filtering."""
    pool = await get_pool()
    if not pool:
        logger.warning("No database connection available")
        return []
    
    # Get dataset info first (inline to avoid circular imports)
    pool = await get_pool()
    if not pool:
        logger.warning("No database connection available")
        return []
    
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
                return []
            
            # Get total queries count
            total_queries = await conn.fetchval("""
                SELECT COUNT(*) as total_queries 
                FROM pg_stat_statements
                WHERE 1=1
                  AND query NOT ILIKE 'EXPLAIN%'
                  AND query NOT ILIKE 'DEALLOCATE%'
                  AND query NOT ILIKE 'SET %'
                  AND query NOT ILIKE 'SHOW %'
                  AND query NOT ILIKE 'BEGIN%'
                  AND query NOT ILIKE 'COMMIT%'
                  AND query NOT ILIKE 'ROLLBACK%'
                  AND query NOT ILIKE 'SAVEPOINT%'
                  AND query NOT ILIKE 'FETCH %'
                  AND query NOT ILIKE 'MOVE %'
                  AND query NOT ILIKE 'DECLARE %'
                  AND query NOT ILIKE '%query-cursor_%'
                  AND query NOT ILIKE 'SELECT%FROM pg\_%'
                  AND query NOT ILIKE 'SELECT%FROM information_schema.%'
                  AND query NOT ILIKE 'SELECT pg\_%(%'
                  AND query NOT ILIKE 'SELECT%FROM pg_show_all_settings%'
                  AND query NOT ILIKE '%pg_settings%'
                  AND query NOT ILIKE 'SELECT rds\_%'
                  AND NOT (query ~* '^\\s*SELECT\\s+\\$[0-9]+')
                  AND query NOT ILIKE 'SET statement_timeout%'
                  AND query NOT ILIKE 'SELECT pg_switch_wal%'
            """)
            
            logger.info(f"pg_stat_statements contains {total_queries} queries")
    except Exception as e:
        logger.error(f"Error checking pg_stat_statements: {e}")
        return []
    
    # Adjust filtering based on dataset size
    if total_queries > SAMPLING_THRESHOLD:
        # Very large dataset - use aggressive filtering
        min_calls = max(MIN_CALLS_FILTER, 10)
        min_time = max(MIN_TIME_FILTER, 5.0)
        limit = min(MAX_QUERIES_DEFAULT, 25000)
        logger.warning(f"Large dataset detected ({total_queries} queries). Using aggressive filtering: min_calls={min_calls}, min_time={min_time}ms, limit={limit}")
    elif total_queries > 50000:
        # Large dataset - use moderate filtering
        min_calls = max(MIN_CALLS_FILTER, 5)
        min_time = max(MIN_TIME_FILTER, 2.0)
        limit = MAX_QUERIES_DEFAULT
        logger.info(f"Medium-large dataset detected ({total_queries} queries). Using moderate filtering: min_calls={min_calls}, min_time={min_time}ms")
    else:
        # Normal dataset - use default filtering
        min_calls = MIN_CALLS_FILTER
        min_time = MIN_TIME_FILTER
        limit = MAX_QUERIES_DEFAULT
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(PG_STAT_QUERY, min_calls, min_time, limit)
        
        # Calculate total time for percentage calculations
        total_time = sum(row['total_time'] for row in rows) if rows else 0
        
        metrics = []
        # Final safety filter in Python for any stragglers
        def _is_system_like(q: str) -> bool:
            ql = q.strip().lower()
            prefixes = (
                'explain', 'deallocate', 'set ', 'show ', 'begin', 'commit', 'rollback',
                'savepoint', 'fetch ', 'move ', 'declare '
            )
            if any(ql.startswith(p) for p in prefixes):
                return True
            if 'query-cursor_' in ql:
                return True
            if ' pg_' in ql or 'information_schema' in ql or 'pg_settings' in ql:
                # Heuristic: exclude queries obviously touching system catalogs
                return True
            if ql.startswith('select $'):
                return True
            if ql.startswith('select pg_') or 'select pg_switch_wal' in ql:
                return True
            return False

        for row in (r for r in rows if not _is_system_like(r['query'])):
            # Calculate percentage of total time
            percentage_of_total_time = (row['total_time'] / total_time * 100) if total_time > 0 else 0
            
            # Create a mock hot_query object for performance score calculation
            hot_query = type('HotQuery', (), {
                'mean_time': row['mean_time'],
                'calls': row['calls'],
                'percentage_of_total_time': percentage_of_total_time,
                'shared_blks_hit': row['shared_blks_hit'],
                'shared_blks_read': row['shared_blks_read'],
                'rows': row['rows']
            })()
            
            # Calculate performance score
            performance_score = round(calculate_performance_score(hot_query, None))
            
            metric = QueryMetrics(
                query_hash=row['query_hash'],
                query_text=row['query'],
                total_time=row['total_time'],
                calls=row['calls'],
                mean_time=row['mean_time'],
                stddev_time=row['stddev_time'],
                min_time=row['min_time'],
                max_time=row['max_time'],
                rows=row['rows'],
                shared_blks_hit=row['shared_blks_hit'],
                shared_blks_read=row['shared_blks_read'],
                shared_blks_written=row['shared_blks_written'],
                shared_blks_dirtied=row['shared_blks_dirtied'],
                temp_blks_read=row['temp_blks_read'],
                temp_blks_written=row['temp_blks_written'],
                blk_read_time=row['blk_read_time'],
                blk_write_time=row['blk_write_time'],
                performance_score=performance_score,
                time_percentage=percentage_of_total_time
            )
            metrics.append(metric)
        
        return metrics

async def poll_pg_stat():
    """Scheduled polling of pg_stat_statements every polling_interval seconds."""
    global metrics_cache, last_updated
    while True:
        try:
            logger.info("Polling pg_stat_statements for query metrics...")
            metrics = await fetch_pg_stat()
            metrics_cache = metrics
            last_updated = datetime.utcnow()
            logger.info(f"Fetched {len(metrics)} query metrics at {last_updated}")
        except Exception as e:
            logger.error(f"Error polling pg_stat_statements: {e}")
        await asyncio.sleep(settings.polling_interval)


def get_metrics_cache() -> List[QueryMetrics]:
    """Get the latest cached query metrics."""
    return metrics_cache

def get_last_updated() -> datetime:
    """Get the last updated timestamp for metrics cache."""
    return last_updated

async def restart_collector():
    """Restart the collector task when database connection changes."""
    global _collector_task, metrics_cache, last_updated
    
    # Cancel existing task if running
    if _collector_task and not _collector_task.done():
        _collector_task.cancel()
        try:
            await _collector_task
        except asyncio.CancelledError:
            pass
    
    # Clear the cache
    metrics_cache = []
    last_updated = None
    
    # Start new collector task
    loop = asyncio.get_event_loop()
    _collector_task = loop.create_task(poll_pg_stat())
    logger.info("✅ Restarted pg_stat_statements polling task")

def initialize_collector():
    """Initialize the collector and register connection change callback."""
    # Register callback for connection changes
    connection_manager.add_connection_change_callback(restart_collector)
    logger.info("✅ Registered collector restart callback")
    
    # Don't start the collector task immediately - wait for connection
    # The collector will be started when a connection is established via the callback
    logger.info("✅ Collector ready - will start when database connection is established") 