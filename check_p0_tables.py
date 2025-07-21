#!/usr/bin/env python3
"""
Check if P0 feature tables exist in the database.
"""

import asyncio
import asyncpg
import os
from typing import List, Dict, Any

async def check_p0_tables():
    """Check if P0 feature tables exist."""
    
    # Get database connection from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        # Check if P0 tables exist
        tables_to_check = [
            'optischema.audit_logs',
            'optischema.connection_baselines', 
            'optischema.index_recommendations'
        ]
        
        print("🔍 Checking P0 feature tables...")
        
        for table in tables_to_check:
            try:
                result = await conn.fetchval(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = '{table.split('.')[0]}' 
                        AND table_name = '{table.split('.')[1]}'
                    )
                """)
                
                if result:
                    print(f"✅ {table} - EXISTS")
                else:
                    print(f"❌ {table} - MISSING")
                    
            except Exception as e:
                print(f"❌ {table} - ERROR: {e}")
        
        # Check if optischema schema exists
        schema_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.schemata 
                WHERE schema_name = 'optischema'
            )
        """)
        
        if schema_exists:
            print("✅ optischema schema - EXISTS")
        else:
            print("❌ optischema schema - MISSING")
        
        await conn.close()
        
        print("\n📋 Summary:")
        print("- If tables are missing, you need to create them in your RDS database")
        print("- You can run the SQL from scripts/init.sql manually")
        print("- Or use the database migration tools")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

if __name__ == "__main__":
    asyncio.run(check_p0_tables()) 