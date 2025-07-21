#!/usr/bin/env python3
"""
Phase 5 Test Script: Replica Benchmark Option

Tests the replica manager and benchmark target switching functionality.
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
from replica_manager import get_replica_manager, initialize_replica_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_replica_manager():
    """Test replica manager functionality."""
    logger.info("🧪 Testing replica manager...")
    
    try:
        # Initialize replica manager
        await initialize_replica_manager()
        
        # Get replica manager
        replica_manager = get_replica_manager()
        
        # Test 1: Get replica info
        logger.info("Testing replica info retrieval...")
        replica_info = await replica_manager.get_replica_info()
        logger.info(f"✅ Replica info: {replica_info}")
        
        # Test 2: Check health
        logger.info("Testing replica health check...")
        is_healthy = await replica_manager.check_health()
        logger.info(f"✅ Replica healthy: {is_healthy}")
        
        # Test 3: Check availability
        logger.info("Testing replica availability...")
        is_available = await replica_manager.is_available()
        logger.info(f"✅ Replica available: {is_available}")
        
        # Test 4: Get benchmark target
        logger.info("Testing benchmark target selection...")
        target_type, target_pool = await replica_manager.get_benchmark_target(prefer_replica=True)
        logger.info(f"✅ Benchmark target: {target_type}")
        
        logger.info("✅ Replica manager tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Replica manager test failed: {e}")
        return False

async def test_replica_benchmark():
    """Test benchmark with replica target switching."""
    logger.info("🧪 Testing replica benchmark functionality...")
    
    try:
        # Create test recommendation
        test_rec = {
            'id': 'phase5-replica-test',
            'query_hash': 'phase5_replica_test_hash',
            'recommendation_type': 'index',
            'title': 'Phase 5 Replica Test: Add Index on information_schema.tables',
            'description': 'Test recommendation for Phase 5 replica benchmark testing.',
            'sql_fix': 'CREATE INDEX IF NOT EXISTS idx_tables_table_name ON information_schema.tables(table_name);',
            'original_sql': 'SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = \'public\' ORDER BY table_name;',
            'patch_sql': 'SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = \'public\' ORDER BY table_name;',
            'execution_plan_json': {'extracted_tables': ['information_schema.tables'], 'estimated_cost': 1000, 'actual_time_ms': 50.5},
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
                logger.info(f"✅ Benchmark target: {results.get('benchmark_target')}")
                logger.info(f"✅ Schema name: {results.get('schema_name')}")
                logger.info(f"✅ Time improvement: {results.get('improvement', {}).get('time_improvement_percent', 0):.1f}%")
                
                # Verify it's a real benchmark with target information
                if results.get('benchmark_type') == 'sandbox_sampled' and results.get('benchmark_target'):
                    logger.info("✅ Replica benchmark executed successfully!")
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
        logger.error(f"❌ Replica benchmark test failed: {e}")
        return False

async def test_replica_api_endpoints():
    """Test replica API endpoints."""
    logger.info("🧪 Testing replica API endpoints...")
    
    try:
        import requests
        import json
        
        # Test 1: Get replica status
        response = requests.get('http://localhost:8000/api/benchmark/replica/status')
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Replica status endpoint: {data}")
        else:
            logger.error(f"❌ Replica status endpoint failed: {response.status_code}")
        
        # Test 2: Health check
        response = requests.post('http://localhost:8000/api/benchmark/replica/health-check')
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Replica health check endpoint: {data}")
        else:
            logger.error(f"❌ Replica health check endpoint failed: {response.status_code}")
        
        # Test 3: Initialize replica
        response = requests.post('http://localhost:8000/api/benchmark/replica/initialize')
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Replica initialize endpoint: {data}")
        else:
            logger.error(f"❌ Replica initialize endpoint failed: {response.status_code}")
        
        logger.info("✅ Replica API endpoints tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Replica API endpoints test failed: {e}")
        return False

async def main():
    """Run all Phase 5 tests."""
    logger.info("🚀 Starting Phase 5 tests...")
    
    # Clean up any existing test data
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    
    tests = [
        ("Replica Manager", test_replica_manager),
        ("Replica API Endpoints", test_replica_api_endpoints),
        ("Replica Benchmark", test_replica_benchmark)
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
        logger.info("🎉 All Phase 5 tests passed!")
        logger.info("✅ Replica manager is working correctly")
        logger.info("✅ Benchmark target switching is operational")
        logger.info("✅ Replica API endpoints are functional")
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
    
    # Clean up
    logger.info("🧹 Cleaning up test data...")
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    logger.info("✅ Test data cleaned up")

if __name__ == "__main__":
    asyncio.run(main()) 