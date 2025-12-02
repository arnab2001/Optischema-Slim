#!/usr/bin/env python3
"""
Generate query activity to populate pg_stat_statements with realistic data
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime, timedelta
import random

async def generate_query_activity(conn):
    """Generate various types of queries to populate statistics."""
    print("🚀 Generating query activity...")
    
    # Run multiple queries to populate pg_stat_statements
    queries = [
        # Fast queries
        "SELECT COUNT(*) FROM demo_users",
        "SELECT COUNT(*) FROM demo_products",
        "SELECT COUNT(*) FROM demo_orders",
        
        # Moderate queries
        "SELECT * FROM demo_users WHERE username LIKE 'user%' LIMIT 10",
        "SELECT * FROM demo_products WHERE category = 'Electronics' LIMIT 10",
        "SELECT * FROM demo_orders WHERE status = 'completed' LIMIT 10",
        
        # Slow queries (intentionally problematic)
        "SELECT u.username, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent FROM demo_users u LEFT JOIN demo_orders o ON u.id = o.user_id WHERE u.created_at > '2024-01-01' GROUP BY u.id, u.username ORDER BY total_spent DESC LIMIT 10",
        
        "SELECT o.id, o.order_date, o.total_amount, (SELECT username FROM demo_users WHERE id = o.user_id) as username FROM demo_orders o WHERE o.order_date > '2024-01-01' LIMIT 100",
        
        "SELECT * FROM demo_products WHERE description LIKE '%electronics%' OR description LIKE '%digital%' OR description LIKE '%smart%'",
        
        "SELECT DATE_TRUNC('day', o.order_date) as day, COUNT(*) as orders, SUM(o.total_amount) as revenue, AVG(o.total_amount) as avg_order_value FROM demo_orders o JOIN demo_users u ON o.user_id = u.id WHERE o.order_date > '2024-01-01' AND u.is_active = true GROUP BY DATE_TRUNC('day', o.order_date) ORDER BY day DESC",
        
        "SELECT username, profile_data->>'location' as location FROM demo_users WHERE profile_data->>'location' = 'US' AND (profile_data->'preferences'->>'theme')::text = '\"dark\"'",
        
        # Complex joins
        "SELECT u.username, p.name as product_name, oi.quantity, oi.price, o.status FROM demo_users u JOIN demo_orders o ON u.id = o.user_id JOIN demo_order_items oi ON o.id = oi.order_id JOIN demo_products p ON oi.product_id = p.id WHERE u.username LIKE 'user%' LIMIT 50",
        
        # Aggregations
        "SELECT category, COUNT(*) as product_count, AVG(price) as avg_price FROM demo_products GROUP BY category ORDER BY avg_price DESC",
        
        "SELECT status, COUNT(*) as order_count, SUM(total_amount) as total_revenue FROM demo_orders GROUP BY status",
        
        # Text search
        "SELECT * FROM demo_products WHERE name ILIKE '%laptop%' OR description ILIKE '%laptop%'",
        
        "SELECT * FROM demo_users WHERE email ILIKE '%@gmail.com'",
        
        # Date range queries
        "SELECT * FROM demo_orders WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31' ORDER BY order_date DESC LIMIT 100",
        
        "SELECT * FROM demo_logs WHERE created_at > NOW() - INTERVAL '7 days' LIMIT 1000",
    ]
    
    # Run each query multiple times to build up statistics
    for i, query in enumerate(queries):
        print(f"Running query {i+1}/{len(queries)}...")
        try:
            # Run the query multiple times to build up call counts
            for _ in range(random.randint(5, 20)):
                await conn.fetch(query)
        except Exception as e:
            print(f"Error running query {i+1}: {e}")
    
    print("✅ Query activity generation completed!")

async def main():
    """Main function."""
    try:
        # Connect to database
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise RuntimeError('DATABASE_URL is not set')
        conn = await asyncpg.connect(database_url)
        
        print("✅ Connected to database")
        
        # Generate query activity
        await generate_query_activity(conn)
        
        print("\n🎯 Query activity generated!")
        print("Check your OptiSchema dashboard for the new data.")
        print("Visit: http://localhost:3000/dashboard")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 
