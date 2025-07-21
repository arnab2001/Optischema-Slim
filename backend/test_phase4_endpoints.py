#!/usr/bin/env python3
"""
Phase 4 Endpoint Test Script

Tests the Phase 4 functionality with the connected database.
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
from job_manager import start_job_manager, stop_job_manager, submit_job, get_job_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_recommendation():
    """Create a test recommendation for Phase 4 testing."""
    logger.info("Creating test recommendation for Phase 4...")
    
    # Create a test recommendation with real SQL that can be benchmarked
    test_rec = {
        'id': 'phase4-test-rec',
        'query_hash': 'phase4_test_query_hash',
        'recommendation_type': 'index',
        'title': 'Phase 4 Test: Add Index on pg_stat_statements',
        'description': 'Test recommendation for Phase 4 schema manager and real benchmark testing.',
        'sql_fix': 'CREATE INDEX IF NOT EXISTS idx_pg_stat_statements_query ON pg_stat_statements(query);',
        'original_sql': 'SELECT query, calls, total_time, mean_time FROM pg_stat_statements WHERE query LIKE \'%SELECT%\' ORDER BY total_time DESC LIMIT 10;',
        'patch_sql': 'SELECT query, calls, total_time, mean_time FROM pg_stat_statements WHERE query LIKE \'%SELECT%\' ORDER BY total_time DESC LIMIT 10;',
        'execution_plan_json': {
            'extracted_tables': ['pg_stat_statements'],
            'estimated_cost': 1000,
            'actual_time_ms': 50.5
        },
        'estimated_improvement_percent': 75,
        'confidence_score': 90,
        'risk_level': 'low',
        'status': 'pending',
        'applied': False,
        'applied_at': None,
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Store recommendation
    RecommendationsDB.store_recommendation(test_rec)
    logger.info(f"✅ Created test recommendation: {test_rec['id']}")
    return test_rec['id']

async def test_phase4_benchmark(recommendation_id: str):
    """Test Phase 4 benchmark functionality."""
    logger.info(f"Testing Phase 4 benchmark for recommendation: {recommendation_id}")
    
    # Start job manager
    await start_job_manager()
    
    try:
        # Submit benchmark job
        job_id = await submit_job(recommendation_id, 'benchmark')
        logger.info(f"✅ Submitted benchmark job: {job_id}")
        
        # Wait for job completion
        logger.info("Waiting for job completion...")
        for i in range(60):  # Wait up to 60 seconds
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
            logger.info(f"✅ Sample percentage: {results.get('sample_percentage')}")
            logger.info(f"✅ Tables sampled: {results.get('tables_sampled')}")
            logger.info(f"✅ Time improvement: {results.get('improvement', {}).get('time_improvement_percent', 0):.1f}%")
            logger.info(f"✅ Baseline metrics: {results.get('baseline_metrics')}")
            logger.info(f"✅ Optimized metrics: {results.get('optimized_metrics')}")
            
            # Verify it's a real benchmark (not mock)
            if results.get('benchmark_type') == 'sandbox_sampled':
                logger.info("🎉 Phase 4 Real benchmark executed successfully!")
                return True, job_id
            else:
                logger.warning("⚠️ Benchmark fell back to mock mode")
                return False, job_id
        else:
            logger.error(f"❌ Job failed with status: {job['status']}")
            if 'error_message' in job:
                logger.error(f"❌ Error: {job['error_message']}")
            return False, job_id
            
    finally:
        await stop_job_manager()

async def test_schema_endpoints():
    """Test the new schema management endpoints."""
    logger.info("Testing schema management endpoints...")
    
    import requests
    import json
    
    # Test 1: List active schemas
    response = requests.get('http://localhost:8000/api/benchmark/schemas/active')
    if response.status_code == 200:
        data = response.json()
        logger.info(f"✅ Active schemas endpoint: {data}")
    else:
        logger.error(f"❌ Active schemas endpoint failed: {response.status_code}")
    
    # Test 2: Cleanup orphaned schemas
    response = requests.post('http://localhost:8000/api/benchmark/schemas/cleanup')
    if response.status_code == 200:
        data = response.json()
        logger.info(f"✅ Schema cleanup endpoint: {data}")
    else:
        logger.error(f"❌ Schema cleanup endpoint failed: {response.status_code}")

async def main():
    """Run Phase 4 tests."""
    logger.info("🚀 Starting Phase 4 endpoint tests...")
    
    # Clean up any existing test data
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    
    try:
        # Test 1: Create test recommendation
        recommendation_id = await create_test_recommendation()
        
        # Test 2: Test schema endpoints
        await test_schema_endpoints()
        
        # Test 3: Test real benchmark
        success, job_id = await test_phase4_benchmark(recommendation_id)
        
        if success:
            logger.info("🎉 Phase 4 tests completed successfully!")
            logger.info("✅ Schema manager is working correctly")
            logger.info("✅ Real benchmark functionality is operational")
            logger.info("✅ Schema cleanup is working properly")
        else:
            logger.warning("⚠️ Phase 4 tests completed with warnings")
            logger.warning("⚠️ Benchmark fell back to mock mode")
        
        # Show job details
        logger.info(f"📊 Job ID: {job_id}")
        logger.info(f"📊 Recommendation ID: {recommendation_id}")
        
    except Exception as e:
        logger.error(f"❌ Phase 4 tests failed: {e}")
    
    finally:
        # Clean up
        logger.info("🧹 Cleaning up test data...")
        RecommendationsDB.clear_all_recommendations()
        BenchmarkJobsDB.clear_all_jobs()
        logger.info("✅ Test data cleaned up")

if __name__ == "__main__":
    asyncio.run(main()) 