#!/usr/bin/env python3
"""
Replica Manager for OptiSchema backend.

Handles replica database connections, health checking, and benchmark target switching.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
import asyncpg
from asyncpg import Pool, Connection
from datetime import datetime, timedelta

from config import get_replica_database_config, settings
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class ReplicaManager:
    """Manages replica database connections and benchmark target switching."""
    
    def __init__(self):
        self._replica_pool: Optional[Pool] = None
        self._replica_config: Optional[Dict[str, Any]] = None
        self._last_health_check: Optional[datetime] = None
        self._health_check_interval = 30  # seconds
        self._is_healthy = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """Initialize replica connection if configured."""
        if not settings.replica_enabled:
            logger.info("Replica benchmarking is disabled")
            return False
        
        replica_config = get_replica_database_config()
        if not replica_config:
            logger.warning("Replica database not configured")
            return False
        
        try:
            async with self._lock:
                # Close existing connection if any
                if self._replica_pool:
                    await self._replica_pool.close()
                
                # Create new connection pool
                pool = await asyncpg.create_pool(
                    host=replica_config['host'],
                    port=replica_config['port'],
                    database=replica_config['database'],
                    user=replica_config['user'],
                    password=replica_config['password'],
                    ssl=replica_config.get('ssl', False),  # Default to False for sandbox
                    min_size=2,
                    max_size=10,
                    command_timeout=30,
                    server_settings={
                        'application_name': 'optischema_replica'
                    }
                )
                
                # Test the connection
                async with pool.acquire() as conn:
                    # Check if pg_stat_statements extension is available
                    extension_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'pg_stat_statements')"
                    )
                    
                    if not extension_exists:
                        await pool.close()
                        logger.error("pg_stat_statements extension not available on replica")
                        return False
                    
                    # Check if extension is enabled
                    extension_enabled = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
                    )
                    
                    if not extension_enabled:
                        # Try to enable the extension
                        try:
                            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                            logger.info("pg_stat_statements extension enabled on replica")
                        except Exception as e:
                            logger.warning(f"Could not enable pg_stat_statements on replica: {e}")
                
                # Update replica connection
                self._replica_pool = pool
                self._replica_config = replica_config.copy()
                self._is_healthy = True
                self._last_health_check = datetime.utcnow()
                
                logger.info(f"Successfully connected to replica: {replica_config['host']}:{replica_config['port']}/{replica_config['database']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to replica: {e}")
            self._is_healthy = False
            return False
    
    async def get_pool(self) -> Optional[Pool]:
        """Get the replica connection pool."""
        if not self._replica_pool or not self._is_healthy:
            # Try to reinitialize if not healthy
            await self.initialize()
        
        return self._replica_pool
    
    async def get_connection(self) -> Optional[Connection]:
        """Get a connection from the replica pool."""
        pool = await self.get_pool()
        if pool:
            return await pool.acquire()
        return None
    
    async def check_health(self) -> bool:
        """Check replica health and update status."""
        if not self._replica_pool:
            self._is_healthy = False
            return False
        
        # Check if we need to perform a health check
        if (self._last_health_check and 
            datetime.utcnow() - self._last_health_check < timedelta(seconds=self._health_check_interval)):
            return self._is_healthy
        
        try:
            async with self._replica_pool.acquire() as conn:
                # Simple health check query
                await conn.fetchval("SELECT 1")
                
                # Check if replica is in recovery mode (read-only) - optional for sandbox databases
                in_recovery = await conn.fetchval("SELECT pg_is_in_recovery()")
                
                if in_recovery:
                    self._is_healthy = True
                    self._last_health_check = datetime.utcnow()
                    logger.debug("Replica health check passed (read replica)")
                    return True
                else:
                    logger.warning("Replica is not in recovery mode (not a read replica) - but allowing for sandbox")
                    self._is_healthy = True
                    self._last_health_check = datetime.utcnow()
                    logger.debug("Replica health check passed (sandbox database)")
                    return True
                    
        except Exception as e:
            logger.error(f"Replica health check failed: {e}")
            self._is_healthy = False
            return False
    
    async def is_available(self) -> bool:
        """Check if replica is available for benchmarking."""
        if not settings.replica_enabled:
            return False
        
        return await self.check_health()
    
    async def get_benchmark_target(self, prefer_replica: bool = True, operation_type: str = "read") -> Tuple[str, Optional[Pool]]:
        """
        Get the appropriate benchmark target (replica or main database).
        
        Args:
            prefer_replica: Whether to prefer replica over main database
            operation_type: Type of operation ("read" or "ddl")
            
        Returns:
            Tuple of (target_type, connection_pool)
        """
        # For DDL operations (CREATE INDEX, etc.), we should NEVER use the main database
        if operation_type == "ddl":
            if await self.is_available():
                pool = await self.get_pool()
                if pool:
                    logger.info("Using replica database for DDL operation")
                    return "replica", pool
            else:
                logger.error("DDL operation requested but no replica available - refusing to use main database")
                return "none", None
        
        # For read operations, we can use replica or main database
        if prefer_replica and await self.is_available():
            pool = await self.get_pool()
            if pool:
                logger.info("Using replica database for read operation")
                return "replica", pool
        
        # For READ operations, we can safely use main database
        if operation_type == "read":
            main_pool = await connection_manager.get_pool()
            if main_pool:
                logger.info("Using main database for read operation (safe)")
                return "main", main_pool
        
        # No available target
        logger.error(f"No benchmark target available for {operation_type} operation")
        return "none", None
    
    async def get_replica_info(self) -> Dict[str, Any]:
        """Get replica information and status."""
        if not settings.replica_enabled:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "Replica benchmarking is disabled"
            }
        
        if not self._replica_config:
            return {
                "enabled": True,
                "status": "not_configured",
                "message": "Replica database not configured"
            }
        
        is_healthy = await self.check_health()
        
        return {
            "enabled": True,
            "status": "healthy" if is_healthy else "unhealthy",
            "config": {
                "host": self._replica_config["host"],
                "port": self._replica_config["port"],
                "database": self._replica_config["database"],
                "user": self._replica_config["user"]
            },
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "health_check_interval": self._health_check_interval,
            "message": "Replica is healthy and available" if is_healthy else "Replica is unhealthy or unavailable"
        }
    
    async def close(self):
        """Close replica connection pool."""
        async with self._lock:
            if self._replica_pool:
                await self._replica_pool.close()
                self._replica_pool = None
                self._replica_config = None
                self._is_healthy = False
                logger.info("Replica connection pool closed")

# Global replica manager instance
_replica_manager: Optional[ReplicaManager] = None

def get_replica_manager() -> ReplicaManager:
    """Get the global replica manager instance."""
    global _replica_manager
    if _replica_manager is None:
        _replica_manager = ReplicaManager()
    return _replica_manager

async def initialize_replica_manager():
    """Initialize the global replica manager."""
    global _replica_manager
    if _replica_manager is None:
        _replica_manager = ReplicaManager()
    
    await _replica_manager.initialize()

async def close_replica_manager():
    """Close the global replica manager."""
    global _replica_manager
    if _replica_manager:
        await _replica_manager.close()
        _replica_manager = None 