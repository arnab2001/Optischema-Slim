"""
Schema Service for OptiSchema Slim.
Fetches table definitions and statistics.
"""

import logging
from typing import List, Dict, Any, Optional
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

class SchemaService:
    async def get_all_tables(self) -> List[str]:
        """List all public tables."""
        pool = await connection_manager.get_pool()
        if not pool:
            return []
            
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_schema, table_name
                """)
                return [f"{row['table_schema']}.{row['table_name']}" for row in rows]
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return []

    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table columns, indexes, and row count estimate."""
        pool = await connection_manager.get_pool()
        if not pool:
            return {}
            
        try:
            async with pool.acquire() as conn:
                # Parse table name (allowing for schema-qualified names)
                if "." in table_name:
                    schema, table = table_name.split(".", 1)
                else:
                    schema, table = "public", table_name

                # Columns
                columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_schema = $1 AND table_name = $2
                    ORDER BY ordinal_position
                """, schema, table)
                
                # Indexes
                indexes = await conn.fetch("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = $1 AND tablename = $2
                """, schema, table)
                
                # Row count estimate (using pg_class and pg_namespace for schema awareness)
                row_count = await conn.fetchval("""
                    SELECT c.reltuples::BIGINT
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = $1 AND c.relname = $2
                """, schema, table)
                
                return {
                    "table_name": table_name,
                    "columns": [dict(c) for c in columns],
                    "indexes": [dict(i) for i in indexes],
                    "row_count": row_count or 0
                }
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return {}

    async def get_context_for_query(self, table_names: List[str]) -> str:
        """
        Get rich context for a list of tables.
        Returns a formatted string for the LLM.
        """
        context_parts = []
        
        for table in table_names:
            info = await self.get_table_info(table)
            if not info:
                continue
                
            # Format columns
            columns_str = ", ".join([
                f"{c['column_name']} ({c['data_type']})" 
                for c in info.get('columns', [])
            ])
            
            # Format indexes
            indexes_str = ", ".join([
                f"{i['indexname']} ({i['indexdef']})" 
                for i in info.get('indexes', [])
            ])
            
            # Format row count
            row_count = info.get('row_count', 0)
            
            context_parts.append(f"""
Table: {table} ({row_count:,} rows)
Columns: {columns_str}
Indexes: {indexes_str}
""")
            
        return "\n".join(context_parts)

schema_service = SchemaService()
