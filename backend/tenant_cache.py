"""
Postgres-backed cache for AI/LLM responses in OptiSchema.
Replaces SQLite cache with tenant-aware Postgres storage.
"""

import os
import time
import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

from config import settings
from tenant_context import TenantContext

logger = logging.getLogger(__name__)

CACHE_TTL = getattr(settings, 'cache_ttl', 3600)  # seconds
CACHE_SIZE = getattr(settings, 'cache_size', 1000)

def make_cache_key(fingerprint: str, analysis_type: str) -> str:
    """Create cache key with tenant prefix."""
    tenant_id = TenantContext.get_tenant_id_or_default()
    return f"{tenant_id}:{fingerprint}:{analysis_type}"

async def get_cache(key: str) -> Optional[str]:
    """
    Get cached value by key for current tenant.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found/expired
    """
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No database connection available for cache lookup")
            return None
        
        tenant_id = TenantContext.get_tenant_id_or_default()
        now = datetime.utcnow()
        
        async with pool.acquire() as conn:
            # Check if cache entry exists and is not expired
            row = await conn.fetchrow(
                """
                SELECT value, created_at FROM optischema.llm_cache 
                WHERE tenant_id = $1 AND key = $2
                """,
                tenant_id,
                key
            )
            
            if row:
                created_at = row['created_at']
                age_seconds = (now - created_at).total_seconds()
                
                if age_seconds < CACHE_TTL:
                    logger.debug(f"Cache hit for key: {key}")
                    return row['value']
                else:
                    # Expired, delete it
                    await delete_cache(key)
                    logger.debug(f"Cache expired for key: {key}")
            
            return None
            
    except Exception as e:
        logger.error(f"Failed to get cache for key {key}: {e}")
        return None

async def set_cache(key: str, value: str):
    """
    Set cached value by key for current tenant.
    
    Args:
        key: Cache key
        value: Value to cache
    """
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No database connection available for cache storage")
            return
        
        tenant_id = TenantContext.get_tenant_id_or_default()
        now = datetime.utcnow()
        
        async with pool.acquire() as conn:
            # Insert or update cache entry
            await conn.execute(
                """
                INSERT INTO optischema.llm_cache (tenant_id, key, value, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, key) 
                DO UPDATE SET value = $3, created_at = $4
                """,
                tenant_id,
                key,
                value,
                now
            )
            
            # Enforce cache size limit per tenant
            await conn.execute(
                """
                DELETE FROM optischema.llm_cache 
                WHERE tenant_id = $1 AND key IN (
                    SELECT key FROM optischema.llm_cache 
                    WHERE tenant_id = $1 
                    ORDER BY created_at ASC 
                    LIMIT (
                        SELECT GREATEST(0, COUNT(*) - $2) 
                        FROM optischema.llm_cache 
                        WHERE tenant_id = $1
                    )
                )
                """,
                tenant_id,
                CACHE_SIZE
            )
            
            logger.debug(f"Cache set for key: {key}")
            
    except Exception as e:
        logger.error(f"Failed to set cache for key {key}: {e}")

async def delete_cache(key: str):
    """
    Delete cached value by key for current tenant.
    
    Args:
        key: Cache key
    """
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No database connection available for cache deletion")
            return
        
        tenant_id = TenantContext.get_tenant_id_or_default()
        
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM optischema.llm_cache WHERE tenant_id = $1 AND key = $2",
                tenant_id,
                key
            )
            
            logger.debug(f"Cache deleted for key: {key}")
            
    except Exception as e:
        logger.error(f"Failed to delete cache for key {key}: {e}")

async def clear_cache():
    """Clear all cache entries for current tenant."""
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No database connection available for cache clearing")
            return
        
        tenant_id = TenantContext.get_tenant_id_or_default()
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM optischema.llm_cache WHERE tenant_id = $1",
                tenant_id
            )
            
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[-1]) if result.startswith("DELETE") else 0
            logger.info(f"Cleared {count} cache entries for tenant {tenant_id}")
            
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")

async def cleanup_expired_cache():
    """Clean up expired cache entries for all tenants."""
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.warning("No database connection available for cache cleanup")
            return
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM optischema.llm_cache 
                WHERE created_at < NOW() - INTERVAL '%s seconds'
                """ % CACHE_TTL
            )
            
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[-1]) if result.startswith("DELETE") else 0
            if count > 0:
                logger.info(f"Cleaned up {count} expired cache entries")
            
    except Exception as e:
        logger.error(f"Failed to cleanup expired cache: {e}")

async def get_cache_stats() -> dict:
    """Get cache statistics for current tenant."""
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            return {"error": "No database connection available"}
        
        tenant_id = TenantContext.get_tenant_id_or_default()
        
        async with pool.acquire() as conn:
            # Get total count
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM optischema.llm_cache WHERE tenant_id = $1",
                tenant_id
            )
            
            # Get expired count
            expired = await conn.fetchval(
                """
                SELECT COUNT(*) FROM optischema.llm_cache 
                WHERE tenant_id = $1 AND created_at < NOW() - INTERVAL '%s seconds'
                """ % CACHE_TTL,
                tenant_id
            )
            
            return {
                "tenant_id": tenant_id,
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "cache_ttl_seconds": CACHE_TTL,
                "max_size": CACHE_SIZE
            }
            
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"error": str(e)}
