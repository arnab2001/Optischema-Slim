"""
Database connection manager for OptiSchema Slim.
Handles the single active database connection.
"""

import logging
import asyncpg
from asyncpg import Pool, Connection
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs

from storage import get_setting, set_setting

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages the single active database connection."""
    
    def __init__(self):
        self._pool: Optional[Pool] = None
        self._config: Optional[Dict[str, Any]] = None
        self._pg_version: Optional[int] = None  # Cached PostgreSQL version number
        
    async def connect(self, connection_string: str) -> Tuple[bool, Optional[str]]:
        """
        Connect to a database using a connection string.
        
        Args:
            connection_string: PostgreSQL connection string
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Parse connection string (basic validation)
            # asyncpg handles parsing well, but we might want to extract components for UI
            # For now, we just pass it to asyncpg
            
            # Close existing pool if any
            if self._pool:
                await self._pool.close()
                self._pool = None
            
            # Create new pool
            pool = await asyncpg.create_pool(
                connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'optischema_slim',
                    'search_path': 'public'
                }
            )
            
            # Test connection and extensions
            async with pool.acquire() as conn:
                # Detect and cache PostgreSQL version (once per connection)
                version_num = await conn.fetchval("SHOW server_version_num")
                if version_num:
                    self._pg_version = int(version_num)
                    logger.info(f"Detected PostgreSQL version: {self._pg_version}")
                else:
                    # Fallback: try to parse from version string
                    version_str = await conn.fetchval("SELECT version()")
                    if version_str:
                        # Extract version number from string like "PostgreSQL 14.5"
                        import re
                        match = re.search(r'PostgreSQL (\d+)\.(\d+)', version_str)
                        if match:
                            major, minor = int(match.group(1)), int(match.group(2))
                            self._pg_version = major * 10000 + minor * 100
                            logger.info(f"Detected PostgreSQL version (parsed): {self._pg_version}")
                
                # Check for pg_stat_statements
                extension_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'pg_stat_statements')"
                )
                
                if not extension_exists:
                    logger.warning("pg_stat_statements extension not available on target DB")
                    # We might still allow connection but warn user? 
                    # For now, let's proceed but log warning.
                
                # Check if enabled
                if extension_exists:
                    extension_enabled = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
                    )
                    if not extension_enabled:
                        try:
                            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                            logger.info("Enabled pg_stat_statements extension")
                        except Exception as e:
                            logger.warning(f"Could not enable pg_stat_statements: {e}")

            # Parse connection string to extract components for UI display
            # Keep the original hostname from connection string for UI/saving
            parsed_config = self._parse_connection_string(connection_string)
            original_host = parsed_config.get('host', 'localhost')
            original_port = parsed_config.get('port', '5432')
            
            # Get actual database name and user from the database (but keep original host/port)
            try:
                async with pool.acquire() as conn:
                    # Get the actual database name (most reliable)
                    actual_db_name = await conn.fetchval("SELECT current_database()")
                    if actual_db_name:
                        parsed_config['database'] = actual_db_name
                    
                    # Get current user
                    current_user = await conn.fetchval("SELECT current_user")
                    if current_user:
                        parsed_config['username'] = current_user
                        parsed_config['user'] = current_user
                    
                    # Store server IP separately (not overwriting original host)
                    server_info = await conn.fetchrow("SELECT inet_server_addr(), inet_server_port()")
                    if server_info:
                        parsed_config['server_ip'] = server_info['inet_server_addr']
                        parsed_config['server_port'] = str(server_info['inet_server_port']) if server_info['inet_server_port'] else original_port
            except Exception as e:
                logger.warning(f"Could not fetch connection details: {e}")
            
            # Ensure original host/port are preserved (important for saving connections)
            parsed_config['host'] = original_host
            parsed_config['port'] = original_port
            
            self._pool = pool
            self._config = {
                'connection_string': connection_string,
                **parsed_config
            }
            
            # Save to storage
            await set_setting('active_connection', connection_string)
            
            logger.info("Successfully connected to database")
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to database: {e}")
            return False, error_msg

    async def get_pool(self) -> Optional[Pool]:
        """Get the current connection pool."""
        if self._pool:
            return self._pool
            
        # Try to load from storage
        connection_string = await get_setting('active_connection')
        if connection_string:
            logger.info("Restoring connection from storage...")
            success, _ = await self.connect(connection_string)
            if success:
                return self._pool
        
        return None

    async def get_connection(self) -> Optional[Connection]:
        """Get a connection from the pool."""
        pool = await self.get_pool()
        if pool:
            return await pool.acquire()
        return None

    async def disconnect(self):
        """Disconnect from the current database."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        
        # Clear cached version on disconnect
        self._pg_version = None
        
        # We might want to clear the setting too, or keep it for next restart?
        # Let's keep it in storage, but clear memory.
        # await set_setting('active_connection', None) 
        logger.info("Disconnected from database")
    
    def get_pg_version(self) -> Optional[int]:
        """Get cached PostgreSQL version number."""
        return self._pg_version
    
    def _parse_connection_string(self, connection_string: str) -> Dict[str, Any]:
        """
        Parse PostgreSQL connection string to extract components.
        Supports both postgresql:// and postgres:// schemes.
        
        Args:
            connection_string: PostgreSQL connection string
            
        Returns:
            Dictionary with parsed connection components
        """
        config: Dict[str, Any] = {
            'host': 'localhost',
            'port': '5432',
            'database': 'postgres',
            'username': 'postgres',
            'user': 'postgres',
        }
        
        try:
            # Handle postgres:// scheme (should be postgresql:// but some drivers use postgres://)
            normalized = connection_string
            if normalized.startswith('postgres://'):
                normalized = normalized.replace('postgres://', 'postgresql://', 1)
            
            # Parse the connection string
            parsed = urlparse(normalized)
            
            if parsed.hostname:
                config['host'] = parsed.hostname
            if parsed.port:
                config['port'] = str(parsed.port)
            if parsed.username:
                config['username'] = parsed.username
                config['user'] = parsed.username
            
            # Database name is in the path (remove leading /)
            if parsed.path:
                db_name = parsed.path.lstrip('/')
                # Remove query parameters if they're in the path (shouldn't happen but handle it)
                if '?' in db_name:
                    db_name = db_name.split('?')[0]
                if db_name:
                    config['database'] = db_name
            
            # Check for SSL in query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'sslmode' in query_params:
                    sslmode = query_params['sslmode'][0].lower()
                    config['ssl'] = sslmode in ('require', 'prefer', 'allow')
            
        except Exception as e:
            logger.warning(f"Could not parse connection string: {e}")
            # Return defaults if parsing fails
        
        return config
    
    def get_connection_config(self) -> Optional[Dict[str, Any]]:
        """Get the current connection configuration."""
        return self._config

    async def check_connection_health(self) -> bool:
        """Check if the current connection is healthy."""
        pool = await self.get_pool()
        if not pool:
            return False
        
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            return False

# Global instance
connection_manager = ConnectionManager()
