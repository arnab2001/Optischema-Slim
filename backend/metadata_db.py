"""
Metadata database connection module for OptiSchema.
Handles connection to the OptiSchema metadata database (separate from target DB).

This database stores:
- Recommendations
- Analysis results
- Audit logs
- Tenant metadata

The target database (user's DB) is read-only and only used for monitoring.
"""

import asyncio
import logging
from typing import Optional
import asyncpg
from asyncpg import Pool

from config import settings

logger = logging.getLogger(__name__)

# Global metadata database pool
_metadata_pool: Optional[Pool] = None
_metadata_lock = asyncio.Lock()


async def initialize_metadata_db() -> bool:
    """
    Initialize connection to OptiSchema metadata database.
    This is separate from the target database being monitored.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global _metadata_pool
    
    async with _metadata_lock:
        if _metadata_pool:
            logger.info("Metadata database already initialized")
            return True
        
        try:
            logger.info("Initializing OptiSchema metadata database connection...")
            
            # Connect to the OptiSchema metadata database (postgres container)
            _metadata_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'optischema_metadata',
                    'search_path': 'optischema,public'
                }
            )
            
            # Verify connection and check for required tables
            async with _metadata_pool.acquire() as conn:
                # Check if optischema schema exists
                schema_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'optischema')"
                )
                
                if not schema_exists:
                    logger.warning("OptiSchema schema does not exist in metadata database")
                    logger.warning("Please run the init.sql script to create required tables")
                    return False
                
                # Check if recommendations table exists
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'optischema' 
                        AND table_name = 'recommendations'
                    )
                    """
                )
                
                if not table_exists:
                    logger.warning("Recommendations table does not exist in metadata database")
                    logger.warning("Please run the init.sql script to create required tables")
                    return False
            
            logger.info("✅ OptiSchema metadata database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize metadata database: {e}")
            _metadata_pool = None
            return False


async def get_metadata_pool() -> Optional[Pool]:
    """
    Get the metadata database connection pool.
    
    Returns:
        Optional[Pool]: The connection pool, or None if not initialized
    """
    if not _metadata_pool:
        logger.warning("Metadata database not initialized, attempting to initialize...")
        await initialize_metadata_db()
    
    return _metadata_pool


async def close_metadata_db():
    """Close the metadata database connection pool."""
    global _metadata_pool
    
    async with _metadata_lock:
        if _metadata_pool:
            await _metadata_pool.close()
            _metadata_pool = None
            logger.info("✅ Metadata database connection closed")


async def health_check_metadata_db() -> bool:
    """
    Check if the metadata database connection is healthy.
    
    Returns:
        bool: True if healthy, False otherwise
    """
    try:
        pool = await get_metadata_pool()
        if not pool:
            return False
        
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
        
    except Exception as e:
        logger.error(f"Metadata database health check failed: {e}")
        return False


# Convenience function for tenant-scoped queries
def get_tenant_filter(tenant_id: str) -> str:
    """
    Get SQL WHERE clause for tenant isolation.
    
    Args:
        tenant_id: The tenant ID to filter by
        
    Returns:
        str: SQL WHERE clause
    """
    return f"tenant_id = '{tenant_id}'"
