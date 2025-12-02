"""
Database context service for gathering schema and statistics information.
Provides rich context for AI recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
import asyncpg
import re

logger = logging.getLogger(__name__)

class DatabaseContextService:
    """Gather database context for AI recommendations."""
    
    @staticmethod
    async def get_table_schema(pool: asyncpg.Pool, table_name: str, schema: str = 'public') -> Dict[str, Any]:
        """
        Get complete table schema information.
        
        Args:
            pool: Database connection pool
            table_name: Name of the table
            schema: Schema name (default: 'public')
            
        Returns:
            Dictionary with table schema details
        """
        async with pool.acquire() as conn:
            try:
                # Get columns with types and constraints
                columns = await conn.fetch("""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = $1 AND table_name = $2
                    ORDER BY ordinal_position
                """, schema, table_name)
                
                # Get primary key
                primary_key = await conn.fetch("""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = $1::regclass AND i.indisprimary
                """, f"{schema}.{table_name}")
                
                # Get foreign keys
                foreign_keys = await conn.fetch("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = $1
                    AND tc.table_name = $2
                """, schema, table_name)
                
                return {
                    "table_name": table_name,
                    "schema": schema,
                    "columns": [dict(col) for col in columns],
                    "primary_key": [pk['attname'] for pk in primary_key],
                    "foreign_keys": [dict(fk) for fk in foreign_keys]
                }
            except Exception as e:
                logger.error(f"Failed to get table schema for {schema}.{table_name}: {e}")
                return {
                    "table_name": table_name,
                    "schema": schema,
                    "columns": [],
                    "primary_key": [],
                    "foreign_keys": [],
                    "error": str(e)
                }
    
    @staticmethod
    async def get_existing_indexes(pool: asyncpg.Pool, table_name: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get all existing indexes for a table.
        
        Args:
            pool: Database connection pool
            table_name: Name of the table
            schema: Schema name (default: 'public')
            
        Returns:
            List of index information dictionaries
        """
        async with pool.acquire() as conn:
            try:
                indexes = await conn.fetch("""
                    SELECT
                        indexname,
                        indexdef,
                        pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
                    FROM pg_indexes
                    WHERE schemaname = $1 AND tablename = $2
                """, schema, table_name)
                
                return [dict(idx) for idx in indexes]
            except Exception as e:
                logger.error(f"Failed to get indexes for {schema}.{table_name}: {e}")
                return []
    
    @staticmethod
    async def get_table_statistics(pool: asyncpg.Pool, table_name: str, schema: str = 'public') -> Dict[str, Any]:
        """
        Get table statistics and data distribution.
        
        Args:
            pool: Database connection pool
            table_name: Name of the table
            schema: Schema name (default: 'public')
            
        Returns:
            Dictionary with table statistics
        """
        async with pool.acquire() as conn:
            try:
                # Get table size and row count
                table_stats = await conn.fetchrow("""
                    SELECT
                        pg_size_pretty(pg_total_relation_size($1::regclass)) as total_size,
                        pg_size_pretty(pg_relation_size($1::regclass)) as table_size,
                        pg_size_pretty(pg_total_relation_size($1::regclass) - pg_relation_size($1::regclass)) as indexes_size,
                        n_live_tup as row_count,
                        n_dead_tup as dead_rows,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables
                    WHERE schemaname = $2 AND relname = $3
                """, f"{schema}.{table_name}", schema, table_name)
                
                # Get column statistics
                column_stats = await conn.fetch("""
                    SELECT
                        attname as column_name,
                        n_distinct,
                        correlation,
                        null_frac
                    FROM pg_stats
                    WHERE schemaname = $1 AND tablename = $2
                """, schema, table_name)
                
                return {
                    "table_stats": dict(table_stats) if table_stats else {},
                    "column_stats": [dict(cs) for cs in column_stats]
                }
            except Exception as e:
                logger.error(f"Failed to get statistics for {schema}.{table_name}: {e}")
                return {
                    "table_stats": {},
                    "column_stats": [],
                    "error": str(e)
                }
    
    @staticmethod
    def extract_table_names(query: str) -> List[tuple]:
        """
        Extract table names from SQL query.
        
        Args:
            query: SQL query string
            
        Returns:
            List of (schema, table) tuples
        """
        # Pattern to match table names in FROM and JOIN clauses
        # Handles: FROM table, FROM schema.table, JOIN table, JOIN schema.table
        table_pattern = r'(?:FROM|JOIN)\s+(?:(\w+)\.)?(\w+)'
        matches = re.findall(table_pattern, query, re.IGNORECASE)
        
        # Filter out common SQL keywords that might be matched
        sql_keywords = {'select', 'where', 'group', 'order', 'having', 'limit', 'offset'}
        
        tables = []
        for schema, table in matches:
            if table.lower() not in sql_keywords:
                tables.append((schema or 'public', table))
        
        return tables
    
    @staticmethod
    async def get_query_context(pool: asyncpg.Pool, query: str) -> Dict[str, Any]:
        """
        Get full context for a query including all referenced tables.
        
        Args:
            pool: Database connection pool
            query: SQL query string
            
        Returns:
            Dictionary with complete query context
        """
        # Extract table names from query
        table_refs = DatabaseContextService.extract_table_names(query)
        
        tables = []
        for schema, table in table_refs:
            try:
                table_info = {
                    "schema_info": await DatabaseContextService.get_table_schema(pool, table, schema),
                    "indexes": await DatabaseContextService.get_existing_indexes(pool, table, schema),
                    "statistics": await DatabaseContextService.get_table_statistics(pool, table, schema)
                }
                tables.append(table_info)
            except Exception as e:
                logger.error(f"Failed to get context for table {schema}.{table}: {e}")
                continue
        
        return {
            "tables": tables,
            "query": query,
            "table_count": len(tables)
        }
    
    @staticmethod
    def format_context_for_prompt(context: Dict[str, Any]) -> Dict[str, str]:
        """
        Format database context into readable strings for LLM prompts.
        
        Args:
            context: Context dictionary from get_query_context
            
        Returns:
            Dictionary with formatted context strings
        """
        schema_parts = []
        index_parts = []
        stats_parts = []
        
        for table_info in context.get('tables', []):
            schema_info = table_info.get('schema_info', {})
            table_name = schema_info.get('table_name', 'unknown')
            
            # Format schema
            columns = schema_info.get('columns', [])
            if columns:
                col_list = [f"  - {col['column_name']} ({col['data_type']})" for col in columns[:10]]
                schema_parts.append(f"Table: {table_name}\n" + "\n".join(col_list))
            
            # Format indexes
            indexes = table_info.get('indexes', [])
            if indexes:
                idx_list = [f"  - {idx['indexname']}" for idx in indexes]
                index_parts.append(f"Table: {table_name}\n" + "\n".join(idx_list))
            
            # Format statistics
            stats = table_info.get('statistics', {}).get('table_stats', {})
            if stats:
                stats_parts.append(
                    f"Table: {table_name}\n"
                    f"  - Rows: {stats.get('row_count', 'unknown')}\n"
                    f"  - Size: {stats.get('total_size', 'unknown')}"
                )
        
        return {
            "schema_context": "\n\n".join(schema_parts) if schema_parts else "No schema information available",
            "existing_indexes": "\n\n".join(index_parts) if index_parts else "No indexes found",
            "table_statistics": "\n\n".join(stats_parts) if stats_parts else "No statistics available"
        }
