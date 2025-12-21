#!/usr/bin/env python3
"""
Complete sync of RDS database to sandbox with table structures and sample data
"""

import asyncio
import asyncpg
import json
import subprocess
import sys
import os

# RDS connection details - use environment variables for security
RDS_HOST = os.getenv("RDS_HOST", "localhost")
RDS_PORT = int(os.getenv("RDS_PORT", "5432"))
RDS_DB = os.getenv("RDS_DB", "postgres")
RDS_USER = os.getenv("RDS_USER", "postgres")
RDS_PASSWORD = os.getenv("RDS_PASSWORD", "")

# Sandbox connection details - use environment variables
SANDBOX_HOST = os.getenv("SANDBOX_HOST", "localhost")
SANDBOX_PORT = int(os.getenv("SANDBOX_PORT", "5433"))
SANDBOX_DB = os.getenv("SANDBOX_DB", "sandbox")
SANDBOX_USER = os.getenv("SANDBOX_USER", "sandbox")
SANDBOX_PASSWORD = os.getenv("SANDBOX_PASSWORD", "sandbox_pass")

async def get_table_structure(conn, schema, table):
    """Get table structure from RDS"""
    try:
        # Get column information
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """, schema, table)
        
        # Get primary key
        pk = await conn.fetch("""
            SELECT column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = $1 AND tc.table_name = $2 
                AND tc.constraint_type = 'PRIMARY KEY'
        """, schema, table)
        
        return {
            'columns': [dict(c) for c in columns],
            'primary_key': [c['column_name'] for c in pk]
        }
    except Exception as e:
        print(f"Error getting structure for {schema}.{table}: {e}")
        return None

async def create_table_in_sandbox(sandbox_conn, schema, table, structure):
    """Create table in sandbox"""
    if not structure:
        return False
        
    try:
        # Build CREATE TABLE statement
        columns = []
        for col in structure['columns']:
            col_def = f'"{col["column_name"]}" {col["data_type"]}'
            if col['is_nullable'] == 'NO':
                col_def += ' NOT NULL'
            if col['column_default']:
                col_def += f' DEFAULT {col["column_default"]}'
            columns.append(col_def)
        
        # Add primary key if exists
        if structure['primary_key']:
            pk_cols = ', '.join([f'"{col}"' for col in structure['primary_key']])
            columns.append(f'PRIMARY KEY ({pk_cols})')
        
        create_sql = f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" (\n  ' + ',\n  '.join(columns) + '\n)'
        
        await sandbox_conn.execute(create_sql)
        print(f"Created table: {schema}.{table}")
        return True
        
    except Exception as e:
        print(f"Error creating table {schema}.{table}: {e}")
        return False

async def copy_sample_data(rds_conn, sandbox_conn, schema, table, limit=100):
    """Copy sample data from RDS to sandbox"""
    try:
        # Get sample data
        data = await rds_conn.fetch(f'SELECT * FROM "{schema}"."{table}" LIMIT {limit}')
        
        if not data:
            return 0
            
        # Get column names
        columns = list(data[0].keys())
        col_names = ', '.join([f'"{col}"' for col in columns])
        
        # Insert data
        values = []
        for row in data:
            row_values = []
            for col in columns:
                value = row[col]
                if value is None:
                    row_values.append('NULL')
                elif isinstance(value, str):
                    row_values.append(f"'{value.replace(chr(39), chr(39)+chr(39))}'")
                else:
                    row_values.append(str(value))
            values.append(f"({', '.join(row_values)})")
        
        if values:
            insert_sql = f'INSERT INTO "{schema}"."{table}" ({col_names}) VALUES {", ".join(values)}'
            await sandbox_conn.execute(insert_sql)
            print(f"Copied {len(data)} rows to {schema}.{table}")
            return len(data)
        
    except Exception as e:
        print(f"Error copying data for {schema}.{table}: {e}")
        return 0

async def main():
    print("Complete sync of RDS database to sandbox...")
    
    # Validate required environment variables
    if not RDS_PASSWORD:
        print("Error: RDS_PASSWORD environment variable is required")
        print("Please set RDS_PASSWORD and other RDS connection variables")
        sys.exit(1)
    
    # Connect to RDS
    print("Connecting to RDS database...")
    try:
        rds_conn = await asyncpg.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=RDS_DB,
            user=RDS_USER,
            password=RDS_PASSWORD,
            ssl='require'
        )
    except Exception as e:
        print(f"Failed to connect to RDS: {e}")
        print("Please check your RDS connection environment variables:")
        print(f"  RDS_HOST={RDS_HOST}")
        print(f"  RDS_PORT={RDS_PORT}")
        print(f"  RDS_DB={RDS_DB}")
        print(f"  RDS_USER={RDS_USER}")
        sys.exit(1)
    
    # Connect to sandbox
    print("Connecting to sandbox...")
    sandbox_conn = await asyncpg.connect(
        host=SANDBOX_HOST,
        port=SANDBOX_PORT,
        database=SANDBOX_DB,
        user=SANDBOX_USER,
        password=SANDBOX_PASSWORD
    )
    
    try:
        # Get all tables
        tables = await rds_conn.fetch("""
            SELECT schemaname, tablename 
            FROM pg_tables 
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            AND schemaname NOT LIKE 'pg_temp_%'
            ORDER BY schemaname, tablename
        """)
        
        print(f"Found {len(tables)} tables to sync")
        
        total_rows = 0
        for table in tables:
            schema, table_name = table['schemaname'], table['tablename']
            print(f"\nProcessing {schema}.{table_name}...")
            
            # Get table structure
            structure = await get_table_structure(rds_conn, schema, table_name)
            
            # Create table in sandbox
            if await create_table_in_sandbox(sandbox_conn, schema, table_name, structure):
                # Copy sample data
                rows_copied = await copy_sample_data(rds_conn, sandbox_conn, schema, table_name, 50)
                total_rows += rows_copied
        
        print(f"\nSync completed!")
        print(f"Total rows copied: {total_rows}")
        print(f"Sandbox: postgresql://{SANDBOX_USER}:***@{SANDBOX_HOST}:{SANDBOX_PORT}/{SANDBOX_DB}")
        print(f"RDS: postgresql://{RDS_USER}:***@{RDS_HOST}:{RDS_PORT}/{RDS_DB}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await rds_conn.close()
        await sandbox_conn.close()

if __name__ == "__main__":
    asyncio.run(main())
