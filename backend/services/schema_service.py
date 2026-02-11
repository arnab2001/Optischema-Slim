"""
Schema Service for OptiSchema Slim.
Fetches table definitions, constraints, statistics, and indexes.
"""

import asyncio
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
        """
        Get rich table information: columns with PK/FK annotations,
        existing indexes, row count estimate, and column cardinality.
        """
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

                # Columns with types
                columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = $1 AND table_name = $2
                    ORDER BY ordinal_position
                """, schema, table)

                # Primary key columns
                pk_columns = await conn.fetch("""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = (
                        SELECT c.oid FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = $1 AND c.relname = $2
                    )
                    AND i.indisprimary
                """, schema, table)
                pk_set = {row['attname'] for row in pk_columns}

                # Foreign key relationships
                foreign_keys = await conn.fetch("""
                    SELECT
                        kcu.column_name,
                        ccu.table_schema AS ref_schema,
                        ccu.table_name AS ref_table,
                        ccu.column_name AS ref_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = $1
                        AND tc.table_name = $2
                """, schema, table)
                fk_map = {
                    row['column_name']: f"{row['ref_table']}.{row['ref_column']}"
                    for row in foreign_keys
                }

                # Column cardinality (n_distinct) from pg_stats
                col_stats = await conn.fetch("""
                    SELECT attname, n_distinct, null_frac
                    FROM pg_stats
                    WHERE schemaname = $1 AND tablename = $2
                """, schema, table)
                stats_map = {
                    row['attname']: {
                        'n_distinct': row['n_distinct'],
                        'null_frac': row['null_frac']
                    }
                    for row in col_stats
                }

                # Existing indexes with key columns
                indexes = await conn.fetch("""
                    SELECT
                        i.indexname,
                        i.indexdef,
                        ix.indisunique,
                        ix.indisprimary,
                        pg_relation_size(ix.indexrelid) as size_bytes,
                        s.idx_scan
                    FROM pg_indexes i
                    JOIN pg_class c ON c.relname = i.indexname
                    JOIN pg_index ix ON ix.indexrelid = c.oid
                    LEFT JOIN pg_stat_user_indexes s
                        ON s.indexrelid = ix.indexrelid
                    WHERE i.schemaname = $1 AND i.tablename = $2
                """, schema, table)

                # Row count estimate
                row_count = await conn.fetchval("""
                    SELECT c.reltuples::BIGINT
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = $1 AND c.relname = $2
                """, schema, table)

                return {
                    "table_name": table_name,
                    "schema": schema,
                    "table": table,
                    "columns": [dict(c) for c in columns],
                    "pk_columns": pk_set,
                    "fk_map": fk_map,
                    "col_stats": stats_map,
                    "indexes": [dict(i) for i in indexes],
                    "row_count": row_count or 0
                }
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return {}

    async def get_context_for_query(self, table_names: List[str]) -> str:
        """
        Get rich context for a list of tables, fetched in parallel.
        Returns a structured, LLM-optimized string with PKs, FKs,
        cardinality, and existing indexes clearly annotated.
        """
        # Fetch all tables in parallel (A2 fix)
        infos = await asyncio.gather(
            *[self.get_table_info(t) for t in table_names]
        )

        context_parts = []

        for info in infos:
            if not info:
                continue

            table_name = info['table_name']
            row_count = info.get('row_count', 0)
            pk_set = info.get('pk_columns', set())
            fk_map = info.get('fk_map', {})
            col_stats = info.get('col_stats', {})

            # Format columns with annotations: PK, FK, cardinality
            col_lines = []
            for c in info.get('columns', []):
                name = c['column_name']
                dtype = c['data_type']
                tags = []

                if name in pk_set:
                    tags.append("PK")
                if name in fk_map:
                    tags.append(f"FK -> {fk_map[name]}")

                # Cardinality hint
                stats = col_stats.get(name)
                if stats and stats['n_distinct'] is not None:
                    nd = stats['n_distinct']
                    if nd >= 0:
                        # Positive = exact distinct count
                        tags.append(f"{int(nd)} distinct")
                    else:
                        # Negative = fraction of rows (e.g. -1.0 = all unique)
                        if nd <= -0.95:
                            tags.append("unique")
                        elif nd <= -0.5:
                            tags.append("high cardinality")
                        else:
                            pct = abs(nd) * 100
                            tags.append(f"~{pct:.0f}% distinct")

                tag_str = f" [{', '.join(tags)}]" if tags else ""
                col_lines.append(f"  - {name} ({dtype}){tag_str}")

            columns_block = "\n".join(col_lines)

            # Format existing indexes with usage stats
            idx_lines = []
            for i in info.get('indexes', []):
                flags = []
                if i.get('indisprimary'):
                    flags.append("PRIMARY")
                elif i.get('indisunique'):
                    flags.append("UNIQUE")

                scans = i.get('idx_scan', 0)
                size_kb = (i.get('size_bytes', 0) or 0) // 1024
                flags.append(f"{scans} scans")
                if size_kb > 0:
                    flags.append(f"{size_kb}KB")

                flag_str = f" [{', '.join(flags)}]" if flags else ""
                idx_lines.append(f"  - {i['indexname']}{flag_str}: {i['indexdef']}")

            indexes_block = "\n".join(idx_lines) if idx_lines else "  (none)"

            context_parts.append(
                f"Table: {table_name} ({row_count:,} rows)\n"
                f"Columns:\n{columns_block}\n"
                f"Existing Indexes:\n{indexes_block}"
            )

        return "\n\n".join(context_parts)


schema_service = SchemaService()
