#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import random
import time
from datetime import datetime, timedelta

async def get_db_connection():
    url = os.getenv('DATABASE_URL')
    if not url:
        # Fallback for dev
        url = "postgresql://optischema:optischema_pass@postgres-sandbox:5432/optischema_sandbox"
    return await asyncpg.connect(url)

async def run_bad_queries(conn):
    """Run a set of intentionally slow/inefficient queries."""
    
    # 1. Unindexed scan on logs
    print(f"[{datetime.now()}] Running unindexed scan on demo_logs...")
    await conn.execute("""
        SELECT action, COUNT(*) 
        FROM demo_logs 
        WHERE user_agent LIKE '%Mozilla%' 
        AND created_at > $1
        GROUP BY action
    """, datetime.now() - timedelta(days=7))

    # 2. Inefficient JOIN without proper indexes
    print(f"[{datetime.now()}] Running large join without indexes...")
    await conn.execute("""
        SELECT u.username, o.total_amount, i.quantity, p.name
        FROM demo_users u
        JOIN demo_orders o ON u.id = o.user_id
        JOIN demo_order_items i ON o.id = i.order_id
        JOIN demo_products p ON i.product_id = p.id
        WHERE o.total_amount > 500
        LIMIT 100
    """)

    # 3. Complex JSONB search on unindexed field
    print(f"[{datetime.now()}] Running slow JSONB search...")
    await conn.execute("""
        SELECT username, profile_data->'preferences'->>'theme'
        FROM demo_users
        WHERE profile_data->>'location' = 'US'
        AND (profile_data->'age')::int > 30
    """)

    # 4. Aggregation on large dataset
    print(f"[{datetime.now()}] Running heavy aggregation...")
    await conn.execute("""
        SELECT 
            date_trunc('hour', created_at) as hr,
            action,
            count(*) as count
        FROM demo_logs
        GROUP BY 1, 2
        ORDER BY count DESC
        LIMIT 50
    """)

async def main():
    print("🚀 Starting Bad Query Load Generator...")
    
    # Wait for DB to be ready and seeded
    retry_count = 0
    conn = None
    while retry_count < 10:
        try:
            conn = await get_db_connection()
            print("✅ Connected to database")
            
            # Check if tables exist (seeding done)
            tables = await conn.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_name = 'demo_logs'")
            if tables > 0:
                break
            print("Waiting for tables to be seeded...")
        except Exception as e:
            print(f"Waiting for DB... ({e})")
        
        await asyncio.sleep(5)
        retry_count += 1

    if not conn:
        print("❌ Could not connect to database. Exiting.")
        return

    try:
        while True:
            try:
                await run_bad_queries(conn)
                # Random sleep between 2-10 seconds to simulate erratic load
                wait_time = random.uniform(2, 10)
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"⚠️ Error running queries: {e}")
                await asyncio.sleep(5)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
