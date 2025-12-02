#!/usr/bin/env python3
"""
Simple query activity generator for OptiSchema demo.
Uses correct column names for the actual demo schema.
"""

import asyncio
import random
import logging
import os
from datetime import datetime, timedelta
import asyncpg
from typing import List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_database_url() -> str:
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL is not set')
    return url

# Simple queries that work with the actual schema
SIMPLE_QUERIES = [
    "SELECT * FROM optischema.demo_users WHERE email = $1",
    "SELECT * FROM optischema.demo_users WHERE created_at > $1 ORDER BY created_at DESC",
    "SELECT COUNT(*) FROM optischema.demo_users WHERE is_active = true",
    "SELECT * FROM optischema.demo_orders WHERE status = $1 ORDER BY order_date DESC",
    "SELECT COUNT(*) FROM optischema.demo_orders WHERE status = 'pending'",
    "SELECT SUM(total_amount) FROM optischema.demo_orders WHERE status = 'completed'",
    "SELECT u.email, COUNT(o.id) as order_count FROM optischema.demo_users u LEFT JOIN optischema.demo_orders o ON u.id = o.user_id GROUP BY u.id, u.email",
    "SELECT status, COUNT(*) as count, AVG(total_amount) as avg_amount FROM optischema.demo_orders GROUP BY status",
    "SELECT u.email, u.created_at, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent FROM optischema.demo_users u LEFT JOIN optischema.demo_orders o ON u.id = o.user_id GROUP BY u.id, u.email, u.created_at HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC",
    "SELECT DATE(order_date) as date, COUNT(*) as orders, SUM(total_amount) as revenue FROM optischema.demo_orders WHERE order_date >= $1 GROUP BY DATE(order_date) ORDER BY date DESC"
]

async def get_connection() -> asyncpg.Connection:
    """Get a database connection."""
    return await asyncpg.connect(_get_database_url())

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
    """Generate random parameters for a query."""
    params = []
    
    if 'email' in query.lower():
        emails = ['user1@example.com', 'user2@example.com', 'admin@company.com', 'test@demo.org']
        params.append(random.choice(emails))
    
    if 'created_at' in query.lower() and '>' in query:
        days_ago = random.randint(1, 30)
        params.append(datetime.now() - timedelta(days=days_ago))
    
    if 'order_date' in query.lower() and '>=' in query:
        days_ago = random.randint(1, 30)
        params.append(datetime.now() - timedelta(days=days_ago))
    
    if 'status' in query.lower():
        statuses = ['pending', 'completed', 'cancelled']
        params.append(random.choice(statuses))
    
    return params

async def run_burst_activity():
    """Run burst activity to quickly populate statistics."""
    logger.info("Running burst activity to populate query statistics...")
    
    conn = await get_connection()
    
    try:
        # Execute multiple queries quickly
        for _ in range(50):
            query = random.choice(SIMPLE_QUERIES)
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
    await run_burst_activity()

if __name__ == "__main__":
    asyncio.run(main()) 
