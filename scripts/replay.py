#!/usr/bin/env python3
"""
OptiSchema Query Replay Script
Continuously generates intentional performance problems for demo purposes.
"""

import asyncio
import asyncpg
import os
import sys
import random
import time
from datetime import datetime, timedelta

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from config import get_database_url
except ImportError:
    # Fallback for when running from scripts directory
    import os
    def get_database_url():
        url = os.getenv('DATABASE_URL')
        if not url:
            raise RuntimeError('DATABASE_URL is not set')
        return url

class QueryReplayer:
    def __init__(self, conn):
        self.conn = conn
        self.running = False
        
    async def generate_slow_queries(self):
        """Generate intentionally slow queries."""
        
        # 1. N+1 Query Problem
        await self.conn.execute("""
            SELECT o.id, o.order_date, o.total_amount,
                   (SELECT username FROM demo_users WHERE id = o.user_id) as username,
                   (SELECT email FROM demo_users WHERE id = o.user_id) as email
            FROM demo_orders o
            WHERE o.order_date > $1
            LIMIT 50
        """, datetime.now() - timedelta(days=7))
        
        # 2. Missing Index Query
        await self.conn.execute("""
            SELECT u.username, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
            FROM demo_users u
            LEFT JOIN demo_orders o ON u.id = o.user_id
            WHERE u.created_at > $1 AND u.is_active = true
            GROUP BY u.id, u.username
            ORDER BY total_spent DESC
            LIMIT 20
        """, datetime.now() - timedelta(days=30))
        
        # 3. Inefficient Text Search
        await self.conn.execute("""
            SELECT * FROM demo_products 
            WHERE description LIKE '%electronics%' 
            OR description LIKE '%digital%'
            OR description LIKE '%smart%'
            OR description LIKE '%wireless%'
            OR description LIKE '%bluetooth%'
        """)
        
        # 4. Complex Aggregation Without Indexes
        await self.conn.execute("""
            SELECT 
                DATE_TRUNC('hour', o.order_date) as hour,
                COUNT(*) as orders,
                SUM(o.total_amount) as revenue,
                AVG(o.total_amount) as avg_order_value,
                COUNT(DISTINCT o.user_id) as unique_users
            FROM demo_orders o
            JOIN demo_users u ON o.user_id = u.id
            WHERE o.order_date > $1
            AND u.is_active = true
            GROUP BY DATE_TRUNC('hour', o.order_date)
            ORDER BY hour DESC
            LIMIT 24
        """, datetime.now() - timedelta(days=1))
        
        # 5. JSON Query Without Index
        await self.conn.execute("""
            SELECT username, profile_data->>'location' as location,
                   profile_data->'preferences'->>'theme' as theme
            FROM demo_users
            WHERE profile_data->>'location' = 'US'
            AND (profile_data->'preferences'->>'theme')::text = '"dark"'
            LIMIT 100
        """)
        
        # 6. Cross Join (Cartesian Product)
        await self.conn.execute("""
            SELECT p.name, c.category, COUNT(*) as count
            FROM demo_products p
            CROSS JOIN (SELECT DISTINCT category FROM demo_products) c
            WHERE p.category = c.category
            GROUP BY p.name, c.category
            LIMIT 50
        """)
        
        # 7. Subquery in WHERE clause
        await self.conn.execute("""
            SELECT * FROM demo_orders o
            WHERE o.user_id IN (
                SELECT id FROM demo_users 
                WHERE created_at > $1 AND is_active = true
            )
            AND o.total_amount > (
                SELECT AVG(total_amount) FROM demo_orders
            )
            LIMIT 100
        """, datetime.now() - timedelta(days=90))
        
        # 8. Window Function Without Proper Indexes
        await self.conn.execute("""
            SELECT 
                username,
                order_date,
                total_amount,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) as rn,
                LAG(total_amount) OVER (PARTITION BY user_id ORDER BY order_date) as prev_amount
            FROM demo_orders o
            JOIN demo_users u ON o.user_id = u.id
            WHERE o.order_date > $1
            LIMIT 200
        """, datetime.now() - timedelta(days=30))

    async def generate_log_queries(self):
        """Generate queries on the logs table (lots of data)."""
        
        # 1. Count by action type
        await self.conn.execute("""
            SELECT action, COUNT(*) as count
            FROM demo_logs
            WHERE created_at > $1
            GROUP BY action
            ORDER BY count DESC
        """, datetime.now() - timedelta(days=1))
        
        # 2. User activity analysis
        await self.conn.execute("""
            SELECT 
                u.username,
                COUNT(l.id) as log_count,
                COUNT(DISTINCT l.action) as unique_actions
            FROM demo_users u
            LEFT JOIN demo_logs l ON u.id = l.user_id
            WHERE l.created_at > $1
            GROUP BY u.id, u.username
            ORDER BY log_count DESC
            LIMIT 50
        """, datetime.now() - timedelta(days=7))
        
        # 3. IP address analysis
        await self.conn.execute("""
            SELECT 
                ip_address,
                COUNT(*) as requests,
                COUNT(DISTINCT user_id) as unique_users
            FROM demo_logs
            WHERE created_at > $1
            GROUP BY ip_address
            ORDER BY requests DESC
            LIMIT 20
        """, datetime.now() - timedelta(days=1))

    async def generate_realistic_workload(self):
        """Generate a realistic e-commerce workload."""
        
        # Simulate user browsing products
        await self.conn.execute("""
            SELECT p.name, p.price, p.category, p.stock_quantity
            FROM demo_products p
            WHERE p.category = $1
            ORDER BY p.price DESC
            LIMIT 20
        """, random.choice(["Electronics", "Clothing", "Books", "Home"]))
        
        # Simulate order history lookup
        await self.conn.execute("""
            SELECT o.order_date, o.total_amount, o.status,
                   COUNT(oi.id) as item_count
            FROM demo_orders o
            LEFT JOIN demo_order_items oi ON o.id = oi.order_id
            WHERE o.user_id = $1
            GROUP BY o.id, o.order_date, o.total_amount, o.status
            ORDER BY o.order_date DESC
            LIMIT 10
        """, random.randint(1, 1000))
        
        # Simulate inventory check
        await self.conn.execute("""
            SELECT p.name, p.stock_quantity, p.price
            FROM demo_products p
            WHERE p.stock_quantity < 10
            ORDER BY p.stock_quantity ASC
            LIMIT 15
        """)

    async def run_replay_cycle(self):
        """Run one cycle of query replay."""
        try:
            # Generate different types of queries
            await self.generate_slow_queries()
            await self.generate_log_queries()
            await self.generate_realistic_workload()
            
            print(f"✅ Generated query batch at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error in replay cycle: {e}")

    async def start_replay(self, interval_seconds=30):
        """Start continuous query replay."""
        self.running = True
        print(f"🚀 Starting query replay (every {interval_seconds} seconds)...")
        print("Press Ctrl+C to stop")
        
        while self.running:
            await self.run_replay_cycle()
            await asyncio.sleep(interval_seconds)
    
    def stop_replay(self):
        """Stop the query replay."""
        self.running = False
        print("\n🛑 Stopping query replay...")

async def main():
    """Main replay function."""
    print("🎭 Starting OptiSchema Query Replay...")
    
    try:
        # Connect to database
        database_url = get_database_url()
        conn = await asyncpg.connect(database_url)
        
        print("✅ Connected to database")
        
        # Create replayer
        replayer = QueryReplayer(conn)
        
        # Handle graceful shutdown
        def signal_handler():
            replayer.stop_replay()
        
        # Start replay
        await replayer.start_replay(interval_seconds=30)
        
    except KeyboardInterrupt:
        print("\n👋 Replay stopped by user")
    except Exception as e:
        print(f"❌ Error in replay: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 
