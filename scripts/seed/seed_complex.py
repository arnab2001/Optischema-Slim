#!/usr/bin/env python3
"""
OptiSchema Complex Demo Data Seeder
Creates a high-volume database with sophisticated performance bottlenecks,
bloat, and complex schema relationships for testing database optimization.
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime, timedelta
import random
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from config import get_database_url
except ImportError:
    def get_database_url():
        url = os.getenv('DATABASE_URL')
        if not url:
            # Try to construct from common env vars or defaults
            user = os.getenv('POSTGRES_USER', 'optischema')
            password = os.getenv('POSTGRES_PASSWORD', 'optischema_pass')
            host = os.getenv('POSTGRES_HOST', 'postgres-sandbox')
            port = os.getenv('POSTGRES_PORT', '5432')
            db = os.getenv('POSTGRES_DB', 'optischema_sandbox')
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return url

async def setup_schema(conn):
    """Create complex schema with multiple tables and relationships."""
    logger.info("Setting up enhanced schema...")
    
    # Enable extensions
    await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
    await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    
    # Drop existing if clean start is needed (optional, handled by TRUNCATE usually)
    # For this script, we'll assume a fresh schema or truncate
    
    await conn.execute("""
        DROP TABLE IF EXISTS demo_metadata CASCADE;
        DROP TABLE IF EXISTS demo_user_activity CASCADE;
        DROP TABLE IF EXISTS demo_reviews CASCADE;
        DROP TABLE IF EXISTS demo_inventory CASCADE;
        DROP TABLE IF EXISTS demo_coupons CASCADE;
        DROP TABLE IF EXISTS demo_order_items CASCADE;
        DROP TABLE IF EXISTS demo_orders CASCADE;
        DROP TABLE IF EXISTS demo_products CASCADE;
        DROP TABLE IF EXISTS demo_users CASCADE;
        DROP TABLE IF EXISTS demo_logs CASCADE;
    """)

    # 1. Users table (with various types for indexing tests)
    await conn.execute("""
        CREATE TABLE demo_users (
            id SERIAL PRIMARY KEY,
            uuid UUID DEFAULT uuid_generate_v4(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) NOT NULL, -- Intentionally NOT unique for testing index need
            password_hash TEXT NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            is_active BOOLEAN DEFAULT true,
            is_staff BOOLEAN DEFAULT false,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            profile_data JSONB
        );
    """)

    # 2. Products table
    await conn.execute("""
        CREATE TABLE demo_products (
            id SERIAL PRIMARY KEY,
            sku VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(100),
            tags TEXT[], -- For array GIN index tests
            attributes JSONB, -- For nested JSONB tests
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Inventory table (Heavy write)
    await conn.execute("""
        CREATE TABLE demo_inventory (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL REFERENCES demo_products(id),
            warehouse_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            reserved_quantity INTEGER NOT NULL DEFAULT 0,
            last_restock TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. Coupons table
    await conn.execute("""
        CREATE TABLE demo_coupons (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            discount_percent INTEGER CHECK (discount_percent > 0 AND discount_percent <= 100),
            valid_from TIMESTAMP NOT NULL,
            valid_to TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT true
        );
    """)

    # 5. Orders table
    await conn.execute("""
        CREATE TABLE demo_orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES demo_users(id),
            coupon_id INTEGER REFERENCES demo_coupons(id),
            order_status VARCHAR(20) DEFAULT 'pending',
            total_amount DECIMAL(10,2) NOT NULL,
            shipping_address TEXT,
            tracking_number VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 6. Order Items table
    await conn.execute("""
        CREATE TABLE demo_order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES demo_orders(id),
            product_id INTEGER NOT NULL REFERENCES demo_products(id),
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0
        );
    """)

    # 7. Reviews table (Text heavy)
    await conn.execute("""
        CREATE TABLE demo_reviews (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL REFERENCES demo_products(id),
            user_id INTEGER NOT NULL REFERENCES demo_users(id),
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            is_verified BOOLEAN DEFAULT false,
            helpful_votes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 8. User Activity (Extremely high volume, intentionally un-indexed on some columns)
    await conn.execute("""
        CREATE TABLE demo_user_activity (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES demo_users(id),
            session_id VARCHAR(100),
            activity_type VARCHAR(50) NOT NULL,
            path TEXT,
            metadata JSONB,
            ip_address INET,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 9. Metadata / System Config (Large JSONB objects)
    await conn.execute("""
        CREATE TABLE demo_metadata (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value JSONB,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

async def seed_users(conn, count=2000):
    logger.info(f"Seeding {count} users...")
    users = []
    for i in range(count):
        username = f"user_{i}_{random.randint(1000, 9999)}"
        email = f"{username}@example.com"
        users.append((
            username,
            email,
            "pbkdf2:sha256:260000$hashedpassword",
            f"First{i}",
            f"Last{i}",
            json.dumps({
                "age": random.randint(18, 70),
                "city": random.choice(["New York", "London", "Paris", "Berlin", "Tokyo"]),
                "last_search": "SQL Optimization",
                "preferences": {"theme": "dark", "notifications": True}
            })
        ))
    
    await conn.executemany("""
        INSERT INTO demo_users (username, email, password_hash, first_name, last_name, profile_data)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, users)

async def seed_products(conn, count=1000):
    logger.info(f"Seeding {count} products...")
    categories = ["Electronics", "Home & Garden", "Books", "Clothing", "Toys", "Health"]
    tags_pool = ["premium", "bestseller", "new", "sale", "eco-friendly", "refurbished"]
    
    products = []
    for i in range(count):
        sku = f"SKU-{i:06d}-{random.randint(10, 99)}"
        products.append((
            sku,
            f"Product {i}",
            f"High quality {random.choice(categories)} product featuring advanced technology and ergonomic design.",
            round(random.uniform(5.0, 2000.0), 2),
            random.choice(categories),
            random.sample(tags_pool, random.randint(1, 3)),
            json.dumps({
                "weight": f"{random.uniform(0.1, 10.0):.2f}kg",
                "color": random.choice(["black", "white", "silver", "red"]),
                "warranty": random.choice(["1 year", "2 years", "None"])
            })
        ))
    
    await conn.executemany("""
        INSERT INTO demo_products (sku, name, description, price, category, tags, attributes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    """, products)

async def seed_inventory(conn):
    logger.info("Seeding inventory...")
    product_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_products")]
    inventory = []
    for pid in product_ids:
        # Multiple warehouses for some products
        for wid in range(1, 3):
            inventory.append((
                pid,
                wid,
                random.randint(0, 1000),
                random.randint(0, 50)
            ))
    
    await conn.executemany("""
        INSERT INTO demo_inventory (product_id, warehouse_id, quantity, reserved_quantity)
        VALUES ($1, $2, $3, $4)
    """, inventory)

async def seed_orders(conn, count=10000):
    logger.info(f"Seeding {count} orders...")
    user_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_users")]
    product_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_products")]
    
    # Create coupons first
    await conn.execute("""
        INSERT INTO demo_coupons (code, discount_percent, valid_from, valid_to)
        VALUES ('SAVE10', 10, NOW() - INTERVAL '1 year', NOW() + INTERVAL '1 year'),
               ('WELCOME20', 20, NOW() - INTERVAL '1 month', NOW() + INTERVAL '11 months'),
               ('EXPIRED', 50, NOW() - INTERVAL '2 years', NOW() - INTERVAL '1 year');
    """)
    coupon_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_coupons")]
    
    for _ in range(count):
        user_id = random.choice(user_ids)
        coupon_id = random.choice(coupon_ids + [None] * 5)
        status = random.choice(['pending', 'shipped', 'delivered', 'cancelled', 'refunded'])
        
        # Insert order
        order = await conn.fetchrow("""
            INSERT INTO demo_orders (user_id, coupon_id, order_status, total_amount, shipping_address)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """, user_id, coupon_id, status, 0, "123 Test St, Sandbox City")
        order_id = order['id']
        
        # Insert items
        num_items = random.randint(1, 5)
        total = 0
        items = []
        for _ in range(num_items):
            pid = random.choice(product_ids)
            qty = random.randint(1, 3)
            price_row = await conn.fetchrow("SELECT price FROM demo_products WHERE id = $1", pid)
            price = price_row['price']
            total += qty * price
            items.append((order_id, pid, qty, price))
            
        await conn.executemany("""
            INSERT INTO demo_order_items (order_id, product_id, quantity, unit_price)
            VALUES ($1, $2, $3, $4)
        """, items)
        
        await conn.execute("UPDATE demo_orders SET total_amount = $1 WHERE id = $2", total, order_id)

async def seed_reviews(conn, count=5000):
    logger.info(f"Seeding {count} reviews...")
    user_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_users")]
    product_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_products")]
    
    reviews = []
    for _ in range(count):
        reviews.append((
            random.choice(product_ids),
            random.choice(user_ids),
            random.randint(1, 5),
            "This product is " + random.choice(["great", "okay", "bad", "amazing", "not worth it"]) + ". " * random.randint(1, 20),
            random.choice([True, False]),
            random.randint(0, 100)
        ))
    
    await conn.executemany("""
        INSERT INTO demo_reviews (product_id, user_id, rating, comment, is_verified, helpful_votes)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, reviews)

async def seed_activity(conn, count=100000):
    logger.info(f"Seeding {count} activity logs (This may take a while)...")
    user_ids = [r['id'] for r in await conn.fetch("SELECT id FROM demo_users")]
    
    # Seeding in batches
    batch_size = 5000
    for i in range(0, count, batch_size):
        activities = []
        for _ in range(min(batch_size, count - i)):
            activities.append((
                random.choice(user_ids),
                f"sess_{random.getrandbits(64)}",
                random.choice(['page_view', 'click', 'add_to_cart', 'search', 'filter']),
                f"/product/{random.randint(1, 1000)}",
                json.dumps({"browser": "Chrome", "os": "Linux"}),
                f"192.168.1.{random.randint(1, 254)}"
            ))
        
        await conn.executemany("""
            INSERT INTO demo_user_activity (user_id, session_id, activity_type, path, metadata, ip_address)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, activities)

async def create_bottlenecks(conn):
    """Intentionally create performance issues."""
    logger.info("Creating intentional performance bottlenecks...")

    # 1. TABLE BLOAT
    # Insert many rows then delete most of them in user_activity
    logger.info("Generating table bloat in demo_user_activity...")
    await conn.execute("""
        INSERT INTO demo_user_activity (user_id, activity_type, path)
        SELECT (id % 1000) + 1, 'bloat_gen', '/bloat'
        FROM generate_series(1, 50000) as id;
    """)
    await conn.execute("DELETE FROM demo_user_activity WHERE activity_type = 'bloat_gen';")
    # This leaves dead tuples

    # 2. INDEX BLOAT
    # Update a column multiple times that has an index (if we added index later, we do it now)
    logger.info("Generating index bloat on demo_inventory...")
    await conn.execute("CREATE INDEX idx_inventory_qty ON demo_inventory(quantity);")
    for _ in range(5):
        await conn.execute("UPDATE demo_inventory SET quantity = quantity + 1;")
    
    # 3. MISSING INDEXES
    # We deliberately didn't add indexes on:
    # - demo_orders(user_id)
    # - demo_reviews(product_id)
    # - demo_user_activity(activity_type)
    # - demo_users(email)
    
    # 4. INEFFICIENT QUERIES (Feed pg_stat_statements)
    logger.info("Executing slow queries to populate pg_stat_statements...")
    
    slow_queries = [
        # Sequential scan on large table
        "SELECT COUNT(*) FROM demo_user_activity WHERE activity_type = 'search';",
        
        # Join without index
        "SELECT u.username, o.total_amount FROM demo_users u JOIN demo_orders o ON u.id = o.user_id WHERE u.email LIKE '%user_1%';",
        
        # Complex aggregation with function on column
        "SELECT DATE_TRUNC('month', created_at), SUM(total_amount) FROM demo_orders GROUP BY 1;",
        
        # Cartesian product (partial) or very large join
        "SELECT count(*) FROM demo_products p1, demo_products p2 WHERE p1.category = p2.category AND p1.id < p2.id LIMIT 1000;",
        
        # JSONB containment without GIN index
        "SELECT username FROM demo_users WHERE profile_data ->> 'city' = 'Berlin';"
    ]
    
    for q in slow_queries:
        try:
            await conn.execute(q)
        except Exception as e:
            logger.warning(f"Query failed as expected or due to error: {e}")

async def main():
    logger.info("Starting COMPLEX Demo Data Seeding...")
    
    try:
        db_url = get_database_url()
        conn = await asyncpg.connect(db_url)
        logger.info("Connected to database")
        
        await setup_schema(conn)
        
        # Seeding
        await seed_users(conn)
        await seed_products(conn)
        await seed_inventory(conn)
        await seed_orders(conn)
        await seed_reviews(conn)
        await seed_activity(conn)
        
        # Optimization challenges
        await create_bottlenecks(conn)
        
        # Analyze to update stats but NOT vacuum (to keep bloat)
        await conn.execute("ANALYZE;")
        
        logger.info("Complex demo data seeding completed successfully!")
        
        # Summary
        summary = await conn.fetchrow("""
            SELECT 
                (SELECT count(*) FROM demo_users) as users,
                (SELECT count(*) FROM demo_products) as products,
                (SELECT count(*) FROM demo_orders) as orders,
                (SELECT count(*) FROM demo_user_activity) as activities
        """)
        logger.info(f"Summary: {summary['users']} users, {summary['products']} products, {summary['orders']} orders, {summary['activities']} activities")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
