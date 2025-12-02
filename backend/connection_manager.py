"""
Database connection manager for OptiSchema backend.
Handles per-tenant database connection pools with database-backed storage.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import asyncpg
from asyncpg import Pool, Connection
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages per-tenant database connections with database-backed storage."""
    
    def __init__(self):
        # Per-tenant connection pools
        self._pools: Dict[str, Pool] = {}  # tenant_id -> Pool
        
        # Legacy support for default tenant (backward compatibility)
        self._current_pool: Optional[Pool] = None
        self._current_config: Optional[Dict[str, Any]] = None
        self._current_tenant_id: Optional[str] = None
        self._current_tenant_name: Optional[str] = None
        
        self._connection_history: list = []
        self._lock = asyncio.Lock()
        self._connection_change_callbacks: list = []
    
    def add_connection_change_callback(self, callback):
        """Add a callback to be called when connection changes."""
        self._connection_change_callbacks.append(callback)
    
    async def _notify_connection_change(self):
        """Notify all callbacks that connection has changed."""
        for callback in self._connection_change_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in connection change callback: {e}")
    
    async def _load_tenant_connection(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Load connection config from database for specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Connection config dict or None
        """
        try:
            from metadata_db import get_metadata_pool
            from encryption_service import EncryptionService
            
            pool = await get_metadata_pool()
            if not pool:
                logger.warning("Metadata database not available")
                return None
            
            # Load most recent active connection for tenant
            row = await pool.fetchrow("""
                SELECT host, port, database_name, username, password, ssl
                FROM optischema.tenant_connections
                WHERE tenant_id = $1 AND is_active = true
                ORDER BY updated_at DESC
                LIMIT 1
            """, tenant_id)
            
            if row:
                # Decrypt password
                encryption_service = EncryptionService()
                decrypted_password = encryption_service.decrypt(row['password'])
                
                return {
                    'host': row['host'],
                    'port': row['port'],
                    'database': row['database_name'],
                    'user': row['username'],
                    'password': decrypted_password,
                    'ssl': row['ssl']
                }
            
            logger.info(f"No active connection found for tenant {tenant_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load tenant connection: {e}")
            return None
    
    async def _create_pool(self, config: Dict[str, Any]) -> Pool:
        """
        Create a connection pool from config.
        
        Args:
            config: Database configuration
            
        Returns:
            Connection pool
        """
        # Prepare SSL configuration
        ssl_config = None
        if config.get('ssl', False):
            ssl_config = 'require'
        
        # Create connection pool
        pool = await asyncpg.create_pool(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            ssl=ssl_config,
            min_size=2,
            max_size=10,
            command_timeout=60,
            server_settings={
                'application_name': 'optischema_backend',
                'search_path': 'public'
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
                raise RuntimeError("pg_stat_statements extension not available")
            
            # Check if extension is enabled
            extension_enabled = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
            )
            
            if not extension_enabled:
                # Try to enable the extension
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                    logger.info("pg_stat_statements extension enabled")
                except Exception as e:
                    logger.warning(f"Could not enable pg_stat_statements: {e}")
        
        return pool
    
    async def connect(
        self,
        config: Dict[str, Any],
        *,
        tenant_id: Optional[str] = None,
        tenant_name: Optional[str] = None
    ) -> bool:
        """
        Connect to a database for a specific tenant.
        
        Args:
            config: Database configuration dictionary
            tenant_id: Tenant identifier
            tenant_name: Tenant name
            
        Returns:
            True if connection successful, False otherwise
        """
        async with self._lock:
            try:
                # Determine tenant context
                resolved_tenant_id = str(tenant_id or settings.default_tenant_id)
                resolved_tenant_name = tenant_name or settings.default_tenant_name
                
                # Close existing pool for this tenant if any
                if resolved_tenant_id in self._pools:
                    await self._pools[resolved_tenant_id].close()
                    del self._pools[resolved_tenant_id]
                
                # Create new connection pool
                pool = await self._create_pool(config)
                
                # Store pool for this tenant
                self._pools[resolved_tenant_id] = pool
                
                # Also update legacy singleton for default tenant (backward compatibility)
                if resolved_tenant_id == str(settings.default_tenant_id):
                    if self._current_pool:
                        await self._current_pool.close()
                    self._current_pool = pool
                    self._current_config = config.copy()
                    self._current_tenant_id = resolved_tenant_id
                    self._current_tenant_name = resolved_tenant_name
                
                # Save connection to database
                await self._save_tenant_connection(
                    tenant_id=resolved_tenant_id,
                    config=config,
                    tenant_name=resolved_tenant_name
                )
                
                # Add to history
                self._connection_history.append({
                    'config': config.copy(),
                    'connected_at': datetime.utcnow(),
                    'status': 'connected',
                    'tenant_id': resolved_tenant_id,
                    'tenant_name': resolved_tenant_name
                })
                
                # Keep only last 10 connections in history
                if len(self._connection_history) > 10:
                    self._connection_history = self._connection_history[-10:]
                
                # Start collector for this tenant
                try:
                    from collector import collector_manager
                    await collector_manager.start_collector(resolved_tenant_id)
                except Exception as e:
                    logger.warning(f"Failed to start collector for tenant {resolved_tenant_id}: {e}")
                
                # Notify about connection change
                await self._notify_connection_change()
                
                logger.info(f"Successfully connected tenant {resolved_tenant_id} to {config['host']}:{config['port']}/{config['database']}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                return False
    
    async def _save_tenant_connection(
        self,
        tenant_id: str,
        config: Dict[str, Any],
        tenant_name: str
    ):
        """
        Save tenant connection to database.
        
        Args:
            tenant_id: Tenant identifier
            config: Connection configuration
            tenant_name: Tenant name
        """
        try:
            from metadata_db import get_metadata_pool
            from encryption_service import EncryptionService
            
            pool = await get_metadata_pool()
            if not pool:
                logger.warning("Metadata database not available, connection not persisted")
                return
            
            # Encrypt password
            encryption_service = EncryptionService()
            encrypted_password = encryption_service.encrypt(config['password'])
            
            # Save to database
            await pool.execute("""
                INSERT INTO optischema.tenant_connections (
                    tenant_id, name, host, port, database_name, 
                    username, password, ssl, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true)
                ON CONFLICT (tenant_id, name) DO UPDATE SET
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    database_name = EXCLUDED.database_name,
                    username = EXCLUDED.username,
                    password = EXCLUDED.password,
                    ssl = EXCLUDED.ssl,
                    is_active = true,
                    updated_at = NOW()
            """, 
                tenant_id,
                tenant_name or "default",
                config['host'],
                config['port'],
                config['database'],
                config['user'],
                encrypted_password,
                config.get('ssl', False)
            )
            
            logger.info(f"Saved connection for tenant {tenant_id} to database")
            
        except Exception as e:
            logger.error(f"Failed to save tenant connection: {e}")
    
    async def get_pool(self, tenant_id: Optional[str] = None) -> Optional[Pool]:
        """
        Get connection pool for specific tenant.
        
        Args:
            tenant_id: Tenant identifier (uses default if None)
            
        Returns:
            Connection pool or None
        """
        # Resolve tenant ID
        if tenant_id is None:
            from tenant_context import TenantContext
            tenant_id = TenantContext.get_tenant_id_or_default()
        
        # Check if pool exists in memory
        if tenant_id in self._pools:
            return self._pools[tenant_id]
        
        # Try to load from database and create pool
        config = await self._load_tenant_connection(tenant_id)
        if config:
            try:
                pool = await self._create_pool(config)
                self._pools[tenant_id] = pool
                logger.info(f"Created pool for tenant {tenant_id} from database config")
                return pool
            except Exception as e:
                logger.error(f"Failed to create pool for tenant {tenant_id}: {e}")
                return None
        
        # Fallback to legacy singleton for default tenant
        if tenant_id == str(settings.default_tenant_id):
            return self._current_pool
        
        return None
    
    async def get_connection(self, tenant_id: Optional[str] = None) -> Optional[Connection]:
        """Get a connection from the pool for specific tenant."""
        pool = await self.get_pool(tenant_id)
        if pool:
            return await pool.acquire()
        return None
    
    def get_current_config(self) -> Optional[Dict[str, Any]]:
        """Get the current database configuration (legacy)."""
        return self._current_config
    
    def get_connection_history(self) -> list:
        """Get the connection history."""
        return self._connection_history.copy()
    
    def clear_connection_history(self):
        """Clear the connection history."""
        self._connection_history.clear()
    
    async def disconnect(self, tenant_id: Optional[str] = None):
        """
        Disconnect from database for specific tenant.
        
        Args:
            tenant_id: Tenant identifier (disconnects all if None)
        """
        async with self._lock:
            if tenant_id:
                # Disconnect specific tenant
                if tenant_id in self._pools:
                    await self._pools[tenant_id].close()
                    del self._pools[tenant_id]
                    logger.info(f"Disconnected tenant {tenant_id}")
            else:
                # Disconnect all tenants
                for tid, pool in list(self._pools.items()):
                    await pool.close()
                self._pools.clear()
                
                # Also clear legacy singleton
                if self._current_pool:
                    await self._current_pool.close()
                    self._current_pool = None
                    self._current_config = None
                    self._current_tenant_id = None
                    self._current_tenant_name = None
                
                logger.info("Disconnected all tenants")
            
            # Stop collectors for disconnected tenants
            try:
                from collector import collector_manager
                if tenant_id:
                    await collector_manager.stop_collector(tenant_id)
                else:
                    # Stop all collectors
                    for tid in list(collector_manager._collectors.keys()):
                        await collector_manager.stop_collector(tid)
            except Exception as e:
                logger.warning(f"Failed to stop collectors: {e}")
            
            # Notify about connection change
            await self._notify_connection_change()
    
    async def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a database connection without switching to it.
        
        Args:
            config: Database configuration to test
            
        Returns:
            Test result dictionary
        """
        try:
            # Prepare SSL configuration
            ssl_config = None
            if config.get('ssl', False):
                ssl_config = 'require'
            
            # Create a temporary connection
            conn = await asyncpg.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                ssl=ssl_config
            )
            
            # Check if pg_stat_statements extension is available
            extension_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'pg_stat_statements')"
            )
            
            # Check if extension is enabled
            extension_enabled = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
            )
            
            # Get database info
            db_info = await conn.fetchrow(
                "SELECT version(), current_database(), current_user"
            )
            
            await conn.close()
            
            return {
                'success': True,
                'message': 'Connection successful',
                'details': {
                    'version': db_info[0],
                    'database': db_info[1],
                    'user': db_info[2],
                    'pg_stat_statements_available': extension_exists,
                    'pg_stat_statements_enabled': extension_enabled
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'details': None
            }
    
    def is_connected(self, tenant_id: Optional[str] = None) -> bool:
        """Check if tenant is connected to a database."""
        if tenant_id is None:
            from tenant_context import TenantContext
            tenant_id = TenantContext.get_tenant_id_or_default()
        
        return tenant_id in self._pools or (
            tenant_id == str(settings.default_tenant_id) and self._current_pool is not None
        )
    
    async def check_connection_health(self, tenant_id: Optional[str] = None) -> bool:
        """Check if the connection for specific tenant is healthy."""
        pool = await self.get_pool(tenant_id)
        if not pool:
            return False
        
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection health check failed for tenant {tenant_id}: {e}")
            # Connection is broken, remove it
            if tenant_id and tenant_id in self._pools:
                del self._pools[tenant_id]
            return False

    def get_current_tenant_id(self) -> Optional[str]:
        """Return the tenant identifier associated with the active connection (legacy)."""
        return self._current_tenant_id

    def get_current_tenant_name(self) -> Optional[str]:
        """Return the tenant name for the active connection (legacy)."""
        return self._current_tenant_name

# Global connection manager instance
connection_manager = ConnectionManager()
