#!/usr/bin/env python3
"""
OptiSchema Demo Data Seeder
Creates realistic database with performance bottlenecks for demo purposes.
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime, timedelta
import random
import json

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

async def create_demo_schema(conn):
    """Create demo tables with realistic structure."""
    
    # Create users table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS demo_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT true,
            profile_data JSONB
        )
    """)
    
    # Create orders table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS demo_orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            shipping_address TEXT,
            billing_address TEXT
        )
    """)
    
    # Create products table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS demo_products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(100),
            stock_quantity INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create order_items table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS demo_order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL
        )
    """)
    
    # Create logs table (for generating lots of data)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS demo_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            action VARCHAR(50) NOT NULL,
            details JSONB,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

async def seed_users(conn, count=1000):
    """Seed users with realistic data."""
    print(f"Seeding {count} users...")
    
    users_data = []
    for i in range(count):
        users_data.append((
            f"user{i:04d}",
            f"user{i:04d}@example.com",
            random.choice([True, False]),
            json.dumps({
                "age": random.randint(18, 80),
                "location": random.choice(["US", "UK", "CA", "AU", "DE"]),
                "preferences": {
                    "theme": random.choice(["light", "dark"]),
                    "notifications": random.choice([True, False])
                }
            })
        ))
    
    await conn.executemany("""
        INSERT INTO demo_users (username, email, is_active, profile_data)
        VALUES ($1, $2, $3, $4)
    """, users_data)

async def seed_products(conn, count=500):
    """Seed products with realistic data."""
    print(f"Seeding {count} products...")
    
    categories = ["Electronics", "Clothing", "Books", "Home", "Sports", "Food", "Beauty"]
    
    products_data = []
    for i in range(count):
        products_data.append((
            f"Product {i:04d}",
            f"This is a description for product {i:04d}",
            round(random.uniform(10.0, 1000.0), 2),
            random.choice(categories),
            random.randint(0, 1000)
        ))
    
    await conn.executemany("""
        INSERT INTO demo_products (name, description, price, category, stock_quantity)
        VALUES ($1, $2, $3, $4, $5)
    """, products_data)

async def seed_orders(conn, count=5000):
    """Seed orders with realistic data."""
    print(f"Seeding {count} orders...")
    
    # Get user IDs
    user_ids = [row['id'] for row in await conn.fetch("SELECT id FROM demo_users")]
    product_ids = [row['id'] for row in await conn.fetch("SELECT id FROM demo_products")]
    
    orders_data = []
    order_items_data = []
    
    for i in range(count):
        user_id = random.choice(user_ids)
        order_date = datetime.now() - timedelta(days=random.randint(0, 365))
        total_amount = 0
        
        # Create order
        order_result = await conn.fetchrow("""
            INSERT INTO demo_orders (user_id, order_date, total_amount, status)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, user_id, order_date, 0, random.choice(['pending', 'completed', 'cancelled']))
        
        order_id = order_result['id']
        
        # Add 1-5 items to each order
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            product_id = random.choice(product_ids)
            quantity = random.randint(1, 10)
            
            # Get product price
            product = await conn.fetchrow("SELECT price FROM demo_products WHERE id = $1", product_id)
            unit_price = product['price']
            
            order_items_data.append((order_id, product_id, quantity, unit_price))
            total_amount += quantity * unit_price
        
        # Update order total
        await conn.execute("UPDATE demo_orders SET total_amount = $1 WHERE id = $2", total_amount, order_id)
    
    # Insert order items in batch
    await conn.executemany("""
        INSERT INTO demo_order_items (order_id, product_id, quantity, unit_price)
        VALUES ($1, $2, $3, $4)
    """, order_items_data)

async def seed_logs(conn, count=50000):
    """Seed logs with realistic data (creates performance bottlenecks)."""
    print(f"Seeding {count} log entries...")
    
    user_ids = [row['id'] for row in await conn.fetch("SELECT id FROM demo_users")]
    actions = ["login", "logout", "view_product", "add_to_cart", "purchase", "search", "profile_update"]
    
    logs_data = []
    for i in range(count):
        logs_data.append((
            random.choice(user_ids) if random.random() > 0.1 else None,  # 10% anonymous
            random.choice(actions),
            json.dumps({
                "page": f"/page/{random.randint(1, 100)}",
                "session_id": f"session_{random.randint(1000, 9999)}",
                "referrer": random.choice([None, "google.com", "facebook.com", "twitter.com"])
            }),
            f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{random.randint(500, 600)}.{random.randint(1, 50)}",
            datetime.now() - timedelta(days=random.randint(0, 30))
        ))
    
    # Insert in batches to avoid memory issues
    batch_size = 1000
    for i in range(0, len(logs_data), batch_size):
        batch = logs_data[i:i + batch_size]
        await conn.executemany("""
            INSERT INTO demo_logs (user_id, action, details, ip_address, user_agent, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, batch)

async def create_performance_bottlenecks(conn):
    """Create intentional performance bottlenecks for demo purposes."""
    print("Creating performance bottlenecks...")
    
    # 1. Create a slow query scenario - no index on commonly queried columns
    await conn.execute("""
        -- This query will be slow due to no index on user_id
        SELECT u.username, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
        FROM demo_users u
        LEFT JOIN demo_orders o ON u.id = o.user_id
        WHERE u.created_at > '2024-01-01'
        GROUP BY u.id, u.username
        ORDER BY total_spent DESC
        LIMIT 10
    """)
    
    # 2. Create N+1 query scenario
    await conn.execute("""
        -- This will generate many individual queries
        SELECT o.id, o.order_date, o.total_amount,
               (SELECT username FROM demo_users WHERE id = o.user_id) as username
        FROM demo_orders o
        WHERE o.order_date > '2024-01-01'
        LIMIT 100
    """)
    
    # 3. Create inefficient text search
    await conn.execute("""
        -- This will be slow due to LIKE on unindexed column
        SELECT * FROM demo_products 
        WHERE description LIKE '%electronics%' 
        OR description LIKE '%digital%'
        OR description LIKE '%smart%'
    """)
    
    # 4. Create complex aggregation without proper indexes
    await conn.execute("""
        -- This will be slow due to complex aggregation
        SELECT 
            DATE_TRUNC('day', o.order_date) as day,
            COUNT(*) as orders,
            SUM(o.total_amount) as revenue,
            AVG(o.total_amount) as avg_order_value
        FROM demo_orders o
        JOIN demo_users u ON o.user_id = u.id
        WHERE o.order_date > '2024-01-01'
        AND u.is_active = true
        GROUP BY DATE_TRUNC('day', o.order_date)
        ORDER BY day DESC
    """)
    
    # 5. Create inefficient JSON query
    await conn.execute("""
        -- This will be slow due to JSON operations
        SELECT username, profile_data->>'location' as location
        FROM demo_users
        WHERE profile_data->>'location' = 'US'
        AND (profile_data->'preferences'->>'theme')::text = '"dark"'
    """)

async def main():
    """Main seeding function."""
    print("🚀 Starting OptiSchema Demo Data Seeding...")
    
    try:
        # Connect to database
        database_url = get_database_url()
        conn = await asyncpg.connect(database_url)
        
        print("✅ Connected to database")
        
        # Create schema
        await create_demo_schema(conn)
        print("✅ Created demo schema")
        
        # Seed data
        await seed_users(conn, 1000)
        await seed_products(conn, 500)
        await seed_orders(conn, 5000)
        await seed_logs(conn, 50000)
        
        # Create performance bottlenecks
        await create_performance_bottlenecks(conn)
        
        print("✅ Demo data seeding completed!")
        print("\n📊 Demo Data Summary:")
        print("- 1,000 users")
        print("- 500 products")
        print("- 5,000 orders")
        print("- 50,000 log entries")
        print("- Performance bottlenecks created for demo")
        
        print("\n🎯 Your OptiSchema dashboard should now show meaningful data!")
        print("Visit: http://localhost:3000/dashboard")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 
