
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://optischema:optischema_pass@localhost:5433/optischema_sandbox")

async def debug_health_queries():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        # 1. Unused Indexes
        print("\n--- Unused Indexes Query ---")
        rows = await conn.fetch("""
            SELECT 
                s.schemaname as schema, 
                s.relname as table, 
                s.indexrelname as index,
                s.idx_scan as scans,
                pg_size_pretty(pg_relation_size(s.indexrelid)) as size
            FROM pg_stat_user_indexes s
            JOIN pg_index i ON s.indexrelid = i.indexrelid
            WHERE s.idx_scan = 0 
            AND i.indisunique = false
            LIMIT 10;
        """)
        if not rows:
            print("No unused indexes found.")
        else:
            for r in rows:
                print(dict(r))

        # 2. Config Settings
        print("\n--- Config Settings Query ---")
        rows = await conn.fetch("""
            SELECT name as setting, setting as current_value, unit 
            FROM pg_settings 
            WHERE name IN ('shared_buffers', 'work_mem', 'maintenance_work_mem', 'effective_cache_size', 'max_connections', 'autovacuum_vacuum_scale_factor');
        """)
        for r in rows:
            print(dict(r))

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_health_queries())
