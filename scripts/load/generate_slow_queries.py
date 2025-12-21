#!/usr/bin/env python3
"""
Generate intentionally slow queries to test the UI performance indicators
"""

import asyncio
import asyncpg
import os
import sys
import time

async def generate_slow_queries(conn):
    """Generate intentionally slow queries."""
    print("🐌 Generating slow queries...")
    
    # Create a large temporary table to make queries slow
    await conn.execute("""
        CREATE TEMP TABLE temp_large_table AS 
        SELECT generate_series(1, 100000) as id, 
               'data_' || generate_series(1, 100000) as data,
               random() as value
    """)
    
    # Slow queries that will take time
    slow_queries = [
        # Cross join to create a large result set
        "SELECT a.id, b.id, a.data, b.data FROM temp_large_table a CROSS JOIN temp_large_table b LIMIT 1000",
        
        # Complex aggregation without indexes
        "SELECT data, COUNT(*), AVG(value), SUM(value), MIN(value), MAX(value) FROM temp_large_table GROUP BY data ORDER BY COUNT(*) DESC LIMIT 100",
        
        # Multiple subqueries
        "SELECT * FROM temp_large_table WHERE id IN (SELECT id FROM temp_large_table WHERE value > 0.5) AND id IN (SELECT id FROM temp_large_table WHERE data LIKE '%1%') LIMIT 1000",
        
        # Window functions on large dataset
        "SELECT id, data, value, ROW_NUMBER() OVER (ORDER BY value DESC) as rn, LAG(value) OVER (ORDER BY id) as prev_value FROM temp_large_table ORDER BY value DESC LIMIT 1000",
        
        # Complex text operations
        "SELECT id, data, value, LENGTH(data) as data_length, UPPER(data) as upper_data, LOWER(data) as lower_data FROM temp_large_table WHERE data LIKE '%1%' OR data LIKE '%2%' OR data LIKE '%3%' ORDER BY data_length DESC LIMIT 1000",
    ]
    
    for i, query in enumerate(slow_queries):
        print(f"Running slow query {i+1}/{len(slow_queries)}...")
        try:
            # Run the query multiple times to build up statistics
            for _ in range(3):
                start_time = time.time()
                await conn.fetch(query)
                elapsed = time.time() - start_time
                print(f"  Query took {elapsed:.2f} seconds")
        except Exception as e:
            print(f"Error running slow query {i+1}: {e}")
    
    print("✅ Slow query generation completed!")

async def main():
    """Main function."""
    try:
        # Connect to database
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise RuntimeError('DATABASE_URL is not set')
        conn = await asyncpg.connect(database_url)
        
        print("✅ Connected to database")
        
        # Generate slow queries
        await generate_slow_queries(conn)
        
        print("\n🎯 Slow queries generated!")
        print("Check your OptiSchema dashboard for red 'Slow' badges.")
        print("Visit: http://localhost:3000/dashboard")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 
