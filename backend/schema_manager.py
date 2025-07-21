#!/usr/bin/env python3
"""
Schema Manager for OptiSchema Benchmark Jobs

Handles temporary schema creation, data sampling, and cleanup for benchmark operations.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Tuple, Any
from contextlib import asynccontextmanager
import asyncpg
from datetime import datetime

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manages temporary schemas for benchmark operations."""
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
        self.active_schemas: Dict[str, Dict[str, Any]] = {}
    
    async def create_temp_schema(self, job_id: str, tables: List[str], sample_percentage: float = 1.0) -> str:
        """
        Create a temporary schema for benchmark operations.
        
        Args:
            job_id: Unique job identifier
            tables: List of table names to sample
            sample_percentage: Percentage of data to sample (1.0 = 100%)
            
        Returns:
            Schema name created
        """
        schema_name = f"benchmark_job_{job_id.replace('-', '_')}"
        
        logger.info(f"Creating temporary schema {schema_name} for job {job_id}")
        
        async with self.pool.acquire() as conn:
            # Create the schema
            await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
            
            # Sample data from each table
            sampled_tables = []
            for table in tables:
                try:
                    # Get table structure
                    columns_query = """
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_schema = $1 AND table_name = $2
                        ORDER BY ordinal_position
                    """
                    columns = await conn.fetch(columns_query, 'public', table)
                    
                    if not columns:
                        logger.warning(f"Table {table} not found, skipping")
                        continue
                    
                    # Create column definitions
                    column_defs = []
                    for col in columns:
                        col_def = f'"{col["column_name"]}" {col["data_type"]}'
                        if col["is_nullable"] == "NO":
                            col_def += " NOT NULL"
                        if col["column_default"]:
                            col_def += f" DEFAULT {col['column_default']}"
                        column_defs.append(col_def)
                    
                    # Create table in temp schema
                    create_table_sql = f'''
                        CREATE TABLE "{schema_name}"."{table}" (
                            {', '.join(column_defs)}
                        )
                    '''
                    await conn.execute(create_table_sql)
                    
                    # Check if it's a table or view
                    is_table = await conn.fetchval('''
                        SELECT EXISTS(
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = $1 AND table_type = 'BASE TABLE'
                        )
                    ''', table)
                    
                    if is_table:
                        # Sample data from original table
                        if sample_percentage < 100.0:
                            sample_sql = f'''
                                INSERT INTO "{schema_name}"."{table}"
                                SELECT * FROM "{table}" TABLESAMPLE SYSTEM ({sample_percentage})
                            '''
                        else:
                            sample_sql = f'''
                                INSERT INTO "{schema_name}"."{table}"
                                SELECT * FROM "{table}"
                            '''
                    else:
                        # For views, just copy all data
                        sample_sql = f'''
                            INSERT INTO "{schema_name}"."{table}"
                            SELECT * FROM "{table}"
                        '''
                    
                    await conn.execute(sample_sql)
                    
                    # Get row count
                    count_result = await conn.fetchval(f'SELECT COUNT(*) FROM "{schema_name}"."{table}"')
                    
                    sampled_tables.append({
                        'name': table,
                        'row_count': count_result,
                        'sample_percentage': sample_percentage
                    })
                    
                    logger.info(f"Sampled {count_result} rows from {table} ({sample_percentage}%)")
                    
                except Exception as e:
                    logger.error(f"Error sampling table {table}: {e}")
                    # Continue with other tables
                    continue
            
            # Store schema info
            self.active_schemas[job_id] = {
                'schema_name': schema_name,
                'created_at': datetime.utcnow(),
                'tables': sampled_tables,
                'sample_percentage': sample_percentage
            }
            
            logger.info(f"Created schema {schema_name} with {len(sampled_tables)} tables")
            return schema_name
    
    async def execute_query_in_schema(self, schema_name: str, query: str, params: Optional[List] = None) -> Tuple[float, Dict[str, Any]]:
        """
        Execute a query in the specified schema and capture performance metrics.
        
        Args:
            schema_name: Schema to execute query in
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Tuple of (execution_time_ms, metrics_dict)
        """
        async with self.pool.acquire() as conn:
            # Enable query timing
            await conn.execute('SET log_statement = \'none\'')
            await conn.execute('SET log_min_duration_statement = 0')
            
            # Get initial stats
            initial_stats = await self._get_connection_stats(conn)
            
            # Execute query with timing
            start_time = datetime.utcnow()
            
            try:
                if params:
                    result = await conn.fetch(query, *params)
                else:
                    result = await conn.fetch(query)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Get final stats
                final_stats = await self._get_connection_stats(conn)
                
                # Calculate metrics
                metrics = {
                    'execution_time_ms': execution_time,
                    'rows_returned': len(result),
                    'shared_buffers_hit': final_stats['shared_buffers_hit'] - initial_stats['shared_buffers_hit'],
                    'shared_buffers_read': final_stats['shared_buffers_read'] - initial_stats['shared_buffers_read'],
                    'temp_files': final_stats['temp_files'] - initial_stats['temp_files'],
                    'temp_bytes': final_stats['temp_bytes'] - initial_stats['temp_bytes'],
                    'blk_read_time_ms': final_stats['blk_read_time_ms'] - initial_stats['blk_read_time_ms'],
                    'blk_write_time_ms': final_stats['blk_write_time_ms'] - initial_stats['blk_write_time_ms']
                }
                
                return execution_time, metrics
                
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.error(f"Query execution failed: {e}")
                raise
    
    async def execute_ddl_in_schema(self, schema_name: str, ddl_query: str) -> bool:
        """
        Execute a DDL operation in the specified schema.
        This method is specifically for DDL operations like CREATE INDEX.
        
        Args:
            schema_name: Schema to execute DDL in
            ddl_query: DDL query to execute
            
        Returns:
            True if successful, False otherwise
        """
        async with self.pool.acquire() as conn:
            try:
                # Set search path to the temporary schema
                await conn.execute(f'SET search_path TO "{schema_name}", public')
                
                # Execute DDL operation
                await conn.execute(ddl_query)
                
                logger.info(f"Successfully executed DDL in schema {schema_name}: {ddl_query[:50]}...")
                return True
                
            except Exception as e:
                logger.error(f"DDL execution failed in schema {schema_name}: {e}")
                return False
    
    async def _get_connection_stats(self, conn) -> Dict[str, int]:
        """Get current connection statistics."""
        try:
            # Try to get database statistics using available functions
            stats = await conn.fetchrow('''
                SELECT 
                    blks_hit as shared_buffers_hit,
                    blks_read as shared_buffers_read,
                    temp_files,
                    temp_bytes,
                    blk_read_time,
                    blk_write_time
                FROM pg_stat_database WHERE datname = current_database()
            ''')
            
            if stats:
                return {
                    'shared_buffers_hit': stats['shared_buffers_hit'] or 0,
                    'shared_buffers_read': stats['shared_buffers_read'] or 0,
                    'temp_files': stats['temp_files'] or 0,
                    'temp_bytes': stats['temp_bytes'] or 0,
                    'blk_read_time_ms': stats['blk_read_time'] or 0,
                    'blk_write_time_ms': stats['blk_write_time'] or 0
                }
        except Exception as e:
            # Fallback to basic stats if detailed stats are not available
            pass
        
        # Fallback: return zero stats
        return {
            'shared_buffers_hit': 0,
            'shared_buffers_read': 0,
            'temp_files': 0,
            'temp_bytes': 0,
            'blk_read_time_ms': 0,
            'blk_write_time_ms': 0
        }
    
    async def drop_temp_schema(self, job_id: str) -> bool:
        """
        Drop temporary schema and cleanup resources.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if successful, False otherwise
        """
        if job_id not in self.active_schemas:
            logger.warning(f"No active schema found for job {job_id}")
            return False
        
        schema_info = self.active_schemas[job_id]
        schema_name = schema_info['schema_name']
        
        logger.info(f"Dropping temporary schema {schema_name} for job {job_id}")
        
        try:
            async with self.pool.acquire() as conn:
                # Drop the schema (this will drop all tables in it)
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                
                # Remove from active schemas
                del self.active_schemas[job_id]
                
                logger.info(f"Successfully dropped schema {schema_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error dropping schema {schema_name}: {e}")
            return False
    
    async def get_schema_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a temporary schema."""
        return self.active_schemas.get(job_id)
    
    async def list_active_schemas(self) -> List[Dict[str, Any]]:
        """List all active temporary schemas."""
        return [
            {
                'job_id': job_id,
                'schema_name': info['schema_name'],
                'created_at': info['created_at'],
                'tables': info['tables'],
                'sample_percentage': info['sample_percentage']
            }
            for job_id, info in self.active_schemas.items()
        ]
    
    async def cleanup_orphaned_schemas(self) -> int:
        """
        Clean up any orphaned temporary schemas that don't have active jobs.
        
        Returns:
            Number of schemas cleaned up
        """
        logger.info("Checking for orphaned temporary schemas...")
        
        async with self.pool.acquire() as conn:
            # Find all benchmark job schemas
            schemas = await conn.fetch('''
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'benchmark_job_%'
            ''')
            
            cleaned_count = 0
            for schema in schemas:
                schema_name = schema['schema_name']
                job_id = schema_name.replace('benchmark_job_', '').replace('_', '-')
                
                # Check if this job is still active
                if job_id not in self.active_schemas:
                    try:
                        await conn.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                        logger.info(f"Cleaned up orphaned schema {schema_name}")
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Error cleaning up schema {schema_name}: {e}")
            
            return cleaned_count

# Global schema manager instance
_schema_manager: Optional[SchemaManager] = None

def get_schema_manager() -> SchemaManager:
    """Get the global schema manager instance."""
    global _schema_manager
    if _schema_manager is None:
        raise RuntimeError("Schema manager not initialized. Call init_schema_manager() first.")
    return _schema_manager

def init_schema_manager(connection_pool: asyncpg.Pool):
    """Initialize the global schema manager."""
    global _schema_manager
    _schema_manager = SchemaManager(connection_pool)
    logger.info("Schema manager initialized") 