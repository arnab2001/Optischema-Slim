"""
Database schema validation script for OptiSchema stateless backend.
Verifies that all tables have proper tenant_id columns and indexes.
"""

import asyncio
import asyncpg
import os
from typing import List, Dict, Any
import sys

async def validate_schema():
    """Validate database schema for stateless operation."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Tables that should have tenant_id
        required_tables = [
            "tenants",
            "tenant_connections",
            "query_metrics",
            "analysis_results",
            "recommendations",
            "sandbox_tests",
            "audit_logs",
            "connection_baselines",
            "index_recommendations",
            "benchmark_jobs",
            "llm_cache"
        ]
        
        print("\n📋 Checking tables for tenant_id column...")
        
        all_valid = True
        for table in required_tables:
            # Check if table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'optischema' 
                    AND table_name = $1
                )
                """,
                table
            )
            
            if not table_exists:
                print(f"⚠️  Table 'optischema.{table}' does not exist")
                continue
            
            # Check for tenant_id column (except tenants table itself)
            if table != "tenants":
                has_tenant_id = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'optischema' 
                        AND table_name = $1 
                        AND column_name = 'tenant_id'
                    )
                    """,
                    table
                )
                
                if has_tenant_id:
                    print(f"✅ optischema.{table} has tenant_id column")
                else:
                    print(f"❌ optischema.{table} is MISSING tenant_id column")
                    all_valid = False
            else:
                print(f"✅ optischema.{table} exists (tenants table)")
        
        # Check for indexes on tenant_id
        print("\n📋 Checking indexes on tenant_id columns...")
        
        indexes = await conn.fetch(
            """
            SELECT 
                t.relname AS table_name,
                i.relname AS index_name,
                a.attname AS column_name
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'optischema'
            AND a.attname = 'tenant_id'
            ORDER BY t.relname, i.relname
            """
        )
        
        if indexes:
            print(f"✅ Found {len(indexes)} indexes on tenant_id columns:")
            for idx in indexes:
                print(f"   - {idx['table_name']}: {idx['index_name']}")
        else:
            print("⚠️  No indexes found on tenant_id columns")
        
        # Check default tenant exists
        print("\n📋 Checking default tenant...")
        
        default_tenant = await conn.fetchrow(
            """
            SELECT id, name FROM optischema.tenants 
            WHERE id = '00000000-0000-0000-0000-000000000001'
            """
        )
        
        if default_tenant:
            print(f"✅ Default tenant exists: {default_tenant['name']}")
        else:
            print("⚠️  Default tenant does not exist")
        
        # Check llm_cache table structure
        print("\n📋 Checking llm_cache table...")
        
        llm_cache_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'optischema' 
                AND table_name = 'llm_cache'
            )
            """
        )
        
        if llm_cache_exists:
            print("✅ llm_cache table exists")
            
            # Check columns
            columns = await conn.fetch(
                """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'optischema' 
                AND table_name = 'llm_cache'
                ORDER BY ordinal_position
                """
            )
            
            print(f"   Columns: {', '.join([col['column_name'] for col in columns])}")
        else:
            print("❌ llm_cache table does not exist")
            all_valid = False
        
        await conn.close()
        
        print("\n" + "="*60)
        if all_valid:
            print("✅ Database schema validation PASSED")
            print("   Backend is ready for stateless operation!")
        else:
            print("❌ Database schema validation FAILED")
            print("   Please run migration scripts to update schema")
        print("="*60)
        
        return all_valid
        
    except Exception as e:
        print(f"❌ Error validating schema: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(validate_schema())
    sys.exit(0 if result else 1)
