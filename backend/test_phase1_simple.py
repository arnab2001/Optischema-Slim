#!/usr/bin/env python3
"""
Simple test script for Phase 1 implementation.
Tests only the SQLite components without full app dependencies.
"""

import logging
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recommendations_db import RecommendationsDB
from benchmark_jobs import BenchmarkJobsDB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_recommendations_storage():
    """Test recommendations storage functionality."""
    logger.info("🧪 Testing recommendations storage...")
    
    # Test storing a recommendation
    test_rec = {
        'id': 'test-rec-001',
        'query_hash': 'test_query_hash_123',
        'recommendation_type': 'index',
        'title': 'Add Index on User Email',
        'description': 'Consider adding an index on the email column to improve query performance.',
        'sql_fix': 'CREATE INDEX idx_users_email ON users(email);',
        'original_sql': 'SELECT * FROM users WHERE email = $1',
        'patch_sql': 'SELECT * FROM users WHERE email = $1',  # Same for index recommendations
        'execution_plan_json': {'tables': ['users'], 'scan_type': 'sequential'},
        'estimated_improvement_percent': 85,
        'confidence_score': 90,
        'risk_level': 'low',
        'status': 'pending'
    }
    
    # Store recommendation
    rec_id = RecommendationsDB.store_recommendation(test_rec)
    logger.info(f"✅ Stored recommendation: {rec_id}")
    
    # Retrieve recommendation
    retrieved_rec = RecommendationsDB.get_recommendation(rec_id)
    if retrieved_rec:
        logger.info(f"✅ Retrieved recommendation: {retrieved_rec['title']}")
    else:
        logger.error("❌ Failed to retrieve recommendation")
        return False
    
    # List recommendations
    recs = RecommendationsDB.list_recommendations(limit=10)
    logger.info(f"✅ Listed {len(recs)} recommendations")
    
    # Update recommendation status
    success = RecommendationsDB.update_recommendation_status(rec_id, 'active')
    if success:
        logger.info("✅ Updated recommendation status")
    else:
        logger.error("❌ Failed to update recommendation status")
        return False
    
    # Get count
    count = RecommendationsDB.get_recommendations_count()
    logger.info(f"✅ Total recommendations: {count}")
    
    return True


def test_benchmark_jobs():
    """Test benchmark jobs functionality."""
    logger.info("🧪 Testing benchmark jobs...")
    
    # Create a job
    job_id = BenchmarkJobsDB.create_job('test-rec-001', 'benchmark')
    logger.info(f"✅ Created benchmark job: {job_id}")
    
    # Get job
    job = BenchmarkJobsDB.get_job(job_id)
    if job:
        logger.info(f"✅ Retrieved job: {job['status']}")
    else:
        logger.error("❌ Failed to retrieve job")
        return False
    
    # Update job status
    success = BenchmarkJobsDB.update_job_status(job_id, 'running')
    if success:
        logger.info("✅ Updated job status to running")
    else:
        logger.error("❌ Failed to update job status")
        return False
    
    # Update with results
    results = {
        'baseline_time': 150.5,
        'optimized_time': 25.2,
        'improvement_percent': 83.2
    }
    success = BenchmarkJobsDB.update_job_status(job_id, 'completed', result=results)
    if success:
        logger.info("✅ Updated job with results")
    else:
        logger.error("❌ Failed to update job with results")
        return False
    
    # List jobs
    jobs = BenchmarkJobsDB.list_jobs(limit=10)
    logger.info(f"✅ Listed {len(jobs)} jobs")
    
    # Get statistics
    stats = BenchmarkJobsDB.get_job_statistics()
    logger.info(f"✅ Job statistics: {stats}")
    
    return True


def test_database_info():
    """Test database information retrieval."""
    logger.info("🧪 Testing database info...")
    
    # Get recommendations database info
    rec_info = RecommendationsDB.get_database_info()
    logger.info(f"✅ Recommendations DB info: {rec_info}")
    
    # Get benchmark jobs statistics
    job_stats = BenchmarkJobsDB.get_job_statistics()
    logger.info(f"✅ Benchmark jobs stats: {job_stats}")
    
    return True


def cleanup_test_data():
    """Clean up test data."""
    logger.info("🧹 Cleaning up test data...")
    
    # Clear all data
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    
    logger.info("✅ Test data cleaned up")


def main():
    """Run all tests."""
    logger.info("🚀 Starting Phase 1 simple tests...")
    
    try:
        # Run tests
        tests = [
            ("Recommendations Storage", test_recommendations_storage),
            ("Benchmark Jobs", test_benchmark_jobs),
            ("Database Info", test_database_info)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                if test_func():
                    logger.info(f"✅ {test_name}: PASSED")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info(f"TEST SUMMARY: {passed}/{total} tests passed")
        logger.info(f"{'='*50}")
        
        if passed == total:
            logger.info("🎉 All tests passed! Phase 1 implementation is working correctly.")
        else:
            logger.error(f"⚠️  {total - passed} tests failed. Please check the implementation.")
        
        # Cleanup
        cleanup_test_data()
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return False
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 