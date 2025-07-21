#!/usr/bin/env python3
"""
Phase 4 Test Script: Sample-Schema Sandbox Benchmark

Tests the schema manager and real benchmark functionality with temporary schemas.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from recommendations_db import RecommendationsDB
from benchmark_jobs import BenchmarkJobsDB
from job_manager import start_job_manager, stop_job_manager, submit_job, get_job_status, list_jobs
from schema_manager import SchemaManager
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'optischema_sandbox',
    'user': 'optischema',
    'password': 'optischema',
    'ssl': False
}

async def setup_test_database():
    """Set up test database with sample tables and data."""
    logger.info("Setting up test database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(**TEST_DB_CONFIG)
        
        # Create test tables
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS test_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS test_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES test_users(id),
                amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert sample data
        await conn.execute('''
            INSERT INTO test_users (name, email) VALUES 
            ('John Doe', 'john@example.com'),
            ('Jane Smith', 'jane@example.com'),
            ('Bob Johnson', 'bob@example.com')
            ON CONFLICT (email) DO NOTHING
        ''')
        
        await conn.execute('''
            INSERT INTO test_orders (user_id, amount, status) VALUES 
            (1, 100.50, 'completed'),
            (1, 250.75, 'pending'),
            (2, 75.25, 'completed'),
            (3, 500.00, 'pending')
            ON CONFLICT DO NOTHING
        ''')
        
        await conn.close()
        logger.info("✅ Test database setup complete")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup test database: {e}")
        raise

async def test_schema_manager():
    """Test schema manager functionality."""
    logger.info("🧪 Testing schema manager...")
    
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(**TEST_DB_CONFIG)
        
        # Create schema manager
        schema_manager = SchemaManager(pool)
        
        # Test 1: Create temporary schema
        logger.info("Testing schema creation...")
        job_id = "test-job-123"
        tables = ["test_users", "test_orders"]
        
        schema_name = await schema_manager.create_temp_schema(job_id, tables, sample_percentage=100.0)
        logger.info(f"✅ Created schema: {schema_name}")
        
        # Test 2: Execute query in schema
        logger.info("Testing query execution...")
        query = "SELECT u.name, COUNT(o.id) as order_count FROM test_users u LEFT JOIN test_orders o ON u.id = o.user_id GROUP BY u.id, u.name"
        
        execution_time, metrics = await schema_manager.execute_query_in_schema(schema_name, query)
        logger.info(f"✅ Query executed in {execution_time:.2f}ms")
        logger.info(f"✅ Metrics: {metrics}")
        
        # Test 3: Get schema info
        logger.info("Testing schema info retrieval...")
        schema_info = await schema_manager.get_schema_info(job_id)
        logger.info(f"✅ Schema info: {schema_info}")
        
        # Test 4: List active schemas
        logger.info("Testing schema listing...")
        active_schemas = await schema_manager.list_active_schemas()
        logger.info(f"✅ Active schemas: {len(active_schemas)}")
        
        # Test 5: Drop schema
        logger.info("Testing schema cleanup...")
        success = await schema_manager.drop_temp_schema(job_id)
        logger.info(f"✅ Schema dropped: {success}")
        
        await pool.close()
        logger.info("✅ Schema manager tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema manager test failed: {e}")
        return False

async def test_real_benchmark():
    """Test real benchmark functionality with schema manager."""
    logger.info("🧪 Testing real benchmark functionality...")
    
    try:
        # Create test recommendation with real SQL
        test_rec = {
            'id': 'test-rec-real-benchmark',
            'query_hash': 'test_query_hash_real',
            'recommendation_type': 'index',
            'title': 'Test Recommendation for Real Benchmark',
            'description': 'Test recommendation for real benchmark testing.',
            'sql_fix': 'CREATE INDEX idx_test_users_email ON test_users(email);',
            'original_sql': 'SELECT * FROM test_users WHERE email = $1',
            'patch_sql': 'SELECT * FROM test_users WHERE email = $1',
            'execution_plan_json': {'extracted_tables': ['test_users']},
            'estimated_improvement_percent': 50,
            'confidence_score': 80,
            'risk_level': 'low',
            'status': 'pending',
            'applied': False,
            'applied_at': None
        }
        
        # Store recommendation
        RecommendationsDB.store_recommendation(test_rec)
        logger.info(f"✅ Created test recommendation: {test_rec['id']}")
        
        # Start job manager
        await start_job_manager()
        
        try:
            # Submit benchmark job
            job_id = await submit_job(test_rec['id'], 'benchmark')
            logger.info(f"✅ Submitted benchmark job: {job_id}")
            
            # Wait for job completion
            logger.info("Waiting for job completion...")
            for i in range(30):  # Wait up to 30 seconds
                job = await get_job_status(job_id)
                if job['status'] in ['completed', 'failed', 'error']:
                    break
                await asyncio.sleep(1)
            
            # Check results
            if job['status'] == 'completed':
                results = job.get('results', {})
                logger.info(f"✅ Job completed successfully")
                logger.info(f"✅ Benchmark type: {results.get('benchmark_type')}")
                logger.info(f"✅ Schema name: {results.get('schema_name')}")
                logger.info(f"✅ Time improvement: {results.get('improvement', {}).get('time_improvement_percent', 0):.1f}%")
                logger.info(f"✅ Baseline metrics: {results.get('baseline_metrics')}")
                logger.info(f"✅ Optimized metrics: {results.get('optimized_metrics')}")
                
                # Verify it's a real benchmark (not mock)
                if results.get('benchmark_type') == 'sandbox_sampled':
                    logger.info("✅ Real benchmark executed successfully!")
                    return True
                else:
                    logger.warning("⚠️ Benchmark fell back to mock mode")
                    return False
            else:
                logger.error(f"❌ Job failed with status: {job['status']}")
                return False
                
        finally:
            await stop_job_manager()
        
    except Exception as e:
        logger.error(f"❌ Real benchmark test failed: {e}")
        return False

async def test_schema_cleanup():
    """Test schema cleanup functionality."""
    logger.info("🧪 Testing schema cleanup...")
    
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(**TEST_DB_CONFIG)
        
        # Create schema manager
        schema_manager = SchemaManager(pool)
        
        # Create some test schemas
        job_ids = ["cleanup-test-1", "cleanup-test-2", "cleanup-test-3"]
        tables = ["test_users"]
        
        for job_id in job_ids:
            await schema_manager.create_temp_schema(job_id, tables, sample_percentage=50.0)
            logger.info(f"✅ Created schema for {job_id}")
        
        # Remove one from active schemas (simulate orphaned schema)
        if "cleanup-test-2" in schema_manager.active_schemas:
            del schema_manager.active_schemas["cleanup-test-2"]
            logger.info("✅ Simulated orphaned schema")
        
        # Test cleanup
        cleaned_count = await schema_manager.cleanup_orphaned_schemas()
        logger.info(f"✅ Cleaned up {cleaned_count} orphaned schemas")
        
        # Clean up remaining schemas
        for job_id in job_ids:
            if job_id in schema_manager.active_schemas:
                await schema_manager.drop_temp_schema(job_id)
        
        await pool.close()
        logger.info("✅ Schema cleanup tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema cleanup test failed: {e}")
        return False

async def main():
    """Run all Phase 4 tests."""
    logger.info("🚀 Starting Phase 4 tests...")
    
    # Clean up any existing test data
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    
    tests = [
        ("Database Setup", setup_test_database),
        ("Schema Manager", test_schema_manager),
        ("Real Benchmark", test_real_benchmark),
        ("Schema Cleanup", test_schema_cleanup)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            if result:
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: FAILED - {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST SUMMARY: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All Phase 4 tests passed!")
        logger.info("✅ Schema manager is working correctly")
        logger.info("✅ Real benchmark functionality is operational")
        logger.info("✅ Schema cleanup is working properly")
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
    
    # Clean up
    logger.info("🧹 Cleaning up test data...")
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    logger.info("✅ Test data cleaned up")

if __name__ == "__main__":
    asyncio.run(main()) 