#!/usr/bin/env python3
"""
Sandbox-specific query activity generator for OptiSchema demo.
Runs in the background to maintain a steady stream of business queries.
"""

import asyncio
import random
import time
import logging
import os
from datetime import datetime, timedelta
import asyncpg
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_sandbox_url() -> str:
    # Prefer replica URL for sandbox, else SANDBOX_DATABASE_URL
    url = os.getenv('REPLICA_DATABASE_URL') or os.getenv('SANDBOX_DATABASE_URL')
    if not url:
        raise RuntimeError('REPLICA_DATABASE_URL or SANDBOX_DATABASE_URL is not set')
    return url

# Business queries that work with the actual sandbox schema
BUSINESS_QUERIES = [
    # User management queries
    "SELECT * FROM users WHERE email = $1",
    "SELECT * FROM users WHERE created_at > $1 ORDER BY created_at DESC",
    "SELECT COUNT(*) FROM users WHERE created_at >= $1",
    "SELECT u.*, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.username, u.email, u.created_at, u.updated_at",
    
    # Order management queries
    "SELECT o.*, u.email FROM orders o JOIN users u ON o.user_id = u.id WHERE o.status = $1 ORDER BY o.created_at DESC",
    "SELECT oi.*, p.name as product_name FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = $1",
    "UPDATE orders SET status = $1 WHERE id = $2",
    "SELECT SUM(amount) FROM orders WHERE created_at >= $1 AND status = 'completed'",
    "SELECT COUNT(*) FROM orders WHERE status = 'pending'",
    
    # Product queries
    "SELECT * FROM products WHERE price BETWEEN $1 AND $2 ORDER BY price DESC",
    "SELECT * FROM products WHERE name ILIKE $1 ORDER BY created_at DESC LIMIT 20",
    "SELECT COUNT(*) FROM products WHERE price > $1",
    "SELECT p.*, COUNT(oi.id) as times_ordered FROM products p LEFT JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id, p.name, p.price, p.created_at ORDER BY times_ordered DESC",
    
    # Analytics queries (these can be slow)
    "SELECT DATE(created_at) as date, COUNT(*) as orders, SUM(amount) as revenue FROM orders WHERE created_at >= $1 GROUP BY DATE(created_at) ORDER BY date DESC",
    "SELECT u.email, COUNT(o.id) as order_count, SUM(o.amount) as total_spent FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at >= $1 GROUP BY u.id, u.email HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC LIMIT 50",
    "SELECT status, COUNT(*) as count, AVG(amount) as avg_amount FROM orders GROUP BY status ORDER BY count DESC",
    
    # Complex joins (slow queries)
    "SELECT u.email, u.created_at, COUNT(o.id) as order_count, SUM(o.amount) as total_spent, AVG(o.amount) as avg_order_value, MAX(o.created_at) as last_order FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at >= $1 GROUP BY u.id, u.email, u.created_at HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC",
    "SELECT p.name, p.price, COUNT(oi.id) as times_ordered, SUM(oi.quantity) as total_quantity FROM products p LEFT JOIN order_items oi ON p.id = oi.product_id LEFT JOIN orders o ON oi.order_id = o.id WHERE o.created_at >= $1 OR o.created_at IS NULL GROUP BY p.id, p.name, p.price ORDER BY total_quantity DESC NULLS LAST"
]

# Slow queries that will trigger performance warnings
SLOW_QUERIES = [
    "SELECT u.email, u.created_at, COUNT(o.id) as order_count, SUM(o.amount) as total_spent, AVG(o.amount) as avg_order_value, MAX(o.created_at) as last_order FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at >= $1 GROUP BY u.id, u.email, u.created_at HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC",
    
    "SELECT DATE_TRUNC('day', o.created_at) as day, COUNT(DISTINCT o.user_id) as unique_customers, COUNT(o.id) as total_orders, SUM(o.amount) as revenue, AVG(o.amount) as avg_order_value FROM orders o WHERE o.created_at >= $1 GROUP BY DATE_TRUNC('day', o.created_at) ORDER BY day DESC",
    
    "SELECT p.name, p.price, COUNT(oi.id) as times_ordered, SUM(oi.quantity) as total_quantity FROM products p LEFT JOIN order_items oi ON p.id = oi.product_id LEFT JOIN orders o ON oi.order_id = o.id WHERE o.created_at >= $1 OR o.created_at IS NULL GROUP BY p.id, p.name, p.price ORDER BY total_quantity DESC NULLS LAST",
    
    "SELECT u.email, COUNT(o.id) as order_count, SUM(o.amount) as total_spent, AVG(o.amount) as avg_order_value FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at >= $1 GROUP BY u.id, u.email HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC LIMIT 50"
]

async def get_connection() -> asyncpg.Connection:
    """Get a database connection."""
    return await asyncpg.connect(_get_sandbox_url())

async def execute_query(conn: asyncpg.Connection, query: str, params: List[Any] = None) -> None:
    """Execute a query with error handling."""
    try:
        if params:
            await conn.execute(query, *params)
        else:
            await conn.execute(query)
    except Exception as e:
        logger.warning(f"Query execution failed: {e}")

async def generate_random_params(query: str) -> List[Any]:
    """Generate random parameters for a query based on its content."""
    params = []
    
    if 'email' in query.lower():
        emails = ['user1@example.com', 'user2@example.com', 'admin@company.com', 'test@demo.org']
        params.append(random.choice(emails))
    
    if 'price' in query.lower() and 'between' in query.lower():
        min_price = random.uniform(10, 50)
        max_price = random.uniform(100, 500)
        params.extend([min_price, max_price])
    elif 'price' in query.lower():
        params.append(random.uniform(10, 200))
    
    if 'created_at' in query.lower() and '>=' in query:
        days_ago = random.randint(1, 30)
        params.append(datetime.now() - timedelta(days=days_ago))
    
    if 'id' in query.lower() and '$1' in query:
        params.append(random.randint(1, 100))
    
    if 'status' in query.lower():
        statuses = ['pending', 'completed', 'cancelled']
        params.append(random.choice(statuses))
    
    if 'name' in query.lower() and 'ILIKE' in query:
        search_terms = ['laptop', 'phone', 'tablet', 'headphones', 'keyboard', 'mouse']
        params.append(f'%{random.choice(search_terms)}%')
    
    # Add more random parameters if needed
    while len(params) < query.count('$'):
        if 'id' in query.lower():
            params.append(random.randint(1, 100))
        elif 'amount' in query.lower():
            params.append(random.uniform(10, 1000))
        else:
            params.append(random.randint(1, 50))
    
    return params

async def run_continuous_activity():
    """Run continuous query activity generation."""
    logger.info("Starting continuous query activity generator for sandbox...")
    
    conn = await get_connection()
    
    try:
        while True:
            # Choose query type based on probability
            if random.random() < 0.15:  # 15% chance of slow query
                query = random.choice(SLOW_QUERIES)
                logger.info("Executing slow query...")
            else:
                query = random.choice(BUSINESS_QUERIES)
            
            # Generate parameters
            params = await generate_random_params(query)
            
            # Execute query
            await execute_query(conn, query, params)
            
            # Random delay between queries (0.5 to 3 seconds)
            delay = random.uniform(0.5, 3.0)
            await asyncio.sleep(delay)
            
    except KeyboardInterrupt:
        logger.info("Stopping continuous activity generator...")
    except Exception as e:
        logger.error(f"Error in continuous activity: {e}")
    finally:
        await conn.close()

async def run_burst_activity():
    """Run burst activity to quickly populate statistics."""
    logger.info("Running burst activity to populate query statistics...")
    
    conn = await get_connection()
    
    try:
        # Execute multiple queries quickly
        for _ in range(50):
            query = random.choice(BUSINESS_QUERIES + SLOW_QUERIES)
            params = await generate_random_params(query)
            await execute_query(conn, query, params)
            
            # Small delay between burst queries
            await asyncio.sleep(0.1)
        
        logger.info("Burst activity completed")
        
    except Exception as e:
        logger.error(f"Error in burst activity: {e}")
    finally:
        await conn.close()

async def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'burst':
        await run_burst_activity()
    else:
        await run_continuous_activity()

if __name__ == "__main__":
    asyncio.run(main()) 
