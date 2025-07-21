#!/usr/bin/env python3
"""
Simple test script for Phase 3 implementation.
Tests async job management functionality.
"""

import asyncio
import logging
import sys
import os
import time

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_manager import (
    start_job_manager,
    stop_job_manager,
    submit_job,
    get_job_status,
    list_jobs,
    cancel_job,
    get_job_manager_status
)
from recommendations_db import RecommendationsDB
from benchmark_jobs import BenchmarkJobsDB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_job_manager_lifecycle():
    """Test job manager startup and shutdown."""
    logger.info("🧪 Testing job manager lifecycle...")
    
    # Start job manager
    await start_job_manager()
    logger.info("✅ Job manager started")
    
    # Check status
    status = get_job_manager_status()
    logger.info(f"✅ Job manager status: {status}")
    
    if status['is_running']:
        logger.info("✅ Job manager is running")
    else:
        logger.error("❌ Job manager is not running")
        return False
    
    # Stop job manager
    await stop_job_manager()
    logger.info("✅ Job manager stopped")
    
    return True


async def test_job_submission():
    """Test job submission and processing."""
    logger.info("🧪 Testing job submission...")
    
    # Start job manager
    await start_job_manager()
    
    try:
        # Create a test recommendation first
        test_rec = {
            'id': 'test-rec-phase3',
            'query_hash': 'test_query_hash_phase3',
            'recommendation_type': 'index',
            'title': 'Test Recommendation for Phase 3',
            'description': 'Test recommendation for job management testing.',
            'sql_fix': 'CREATE INDEX idx_test_phase3 ON test_table(column1);',
            'original_sql': 'SELECT * FROM test_table WHERE column1 = $1',
            'patch_sql': 'SELECT * FROM test_table WHERE column1 = $1',
            'execution_plan_json': {'extracted_tables': ['test_table']},
            'estimated_improvement_percent': 75,
            'confidence_score': 85,
            'risk_level': 'low',
            'status': 'pending'
        }
        
        rec_id = RecommendationsDB.store_recommendation(test_rec)
        logger.info(f"✅ Created test recommendation: {rec_id}")
        
        # Submit a benchmark job
        job_id = await submit_job(rec_id, 'benchmark')
        logger.info(f"✅ Submitted benchmark job: {job_id}")
        
        # Wait a bit for job to start processing
        await asyncio.sleep(1)
        
        # Check job status
        job = await get_job_status(job_id)
        logger.info(f"✅ Job status: {job['status']}")
        
        if job['status'] in ['pending', 'running']:
            logger.info("✅ Job is being processed")
        else:
            logger.error(f"❌ Unexpected job status: {job['status']}")
            return False
        
        # Wait for job to complete
        max_wait = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job = await get_job_status(job_id)
            if job['status'] == 'completed':
                logger.info("✅ Job completed successfully")
                logger.info(f"✅ Job results: {job.get('result_json', {})}")
                break
            elif job['status'] in ['failed', 'error']:
                logger.error(f"❌ Job failed: {job.get('error_message', 'Unknown error')}")
                return False
            
            await asyncio.sleep(0.5)
        else:
            logger.error("❌ Job did not complete within timeout")
            return False
        
        return True
        
    finally:
        # Stop job manager
        await stop_job_manager()


async def test_job_cancellation():
    """Test job cancellation."""
    logger.info("🧪 Testing job cancellation...")
    
    # Start job manager
    await start_job_manager()
    
    # Create a test recommendation
    test_rec = {
        'id': 'test-rec-cancel',
        'query_hash': 'test_query_hash_cancel',
        'recommendation_type': 'index',
        'title': 'Test Recommendation for Cancellation',
        'description': 'Test recommendation for cancellation testing.',
        'sql_fix': 'CREATE INDEX idx_test_cancel ON test_table(column2);',
        'original_sql': 'SELECT * FROM test_table WHERE column2 = $1',
        'patch_sql': 'SELECT * FROM test_table WHERE column2 = $1',
        'execution_plan_json': {'extracted_tables': ['test_table']},
        'estimated_improvement_percent': 60,
        'confidence_score': 70,
        'risk_level': 'medium',
        'status': 'pending'
    }
    
    rec_id = RecommendationsDB.store_recommendation(test_rec)
    logger.info(f"✅ Created test recommendation: {rec_id}")
    
    # Submit a job
    job_id = await submit_job(rec_id, 'benchmark')
    logger.info(f"✅ Submitted job: {job_id}")
    
    # Wait a bit for job to start
    await asyncio.sleep(0.5)
    
    # Check job status before cancellation
    job = await get_job_status(job_id)
    logger.info(f"✅ Job status before cancellation: {job['status']}")
    
    # Cancel the job (only if it's still active)
    if job['status'] in ['pending', 'running']:
        try:
            success = await cancel_job(job_id)
            if success:
                logger.info("✅ Job cancelled successfully")
            else:
                logger.warning("⚠️ Job could not be cancelled (may have already completed)")
        except Exception as e:
            logger.error(f"❌ Error cancelling job: {e}")
            await stop_job_manager()
            return False
    else:
        logger.info("✅ Job already completed, no need to cancel")
    
    # Wait a bit for cancellation to process
    await asyncio.sleep(0.5)
    
    # Check final status
    try:
        job = await get_job_status(job_id)
        logger.info(f"✅ Final job status: {job['status']}")
        
        # Verify the job exists in database
        if job is None:
            logger.error("❌ Job not found in database")
            await stop_job_manager()
            return False
    except Exception as e:
        logger.error(f"❌ Error getting job status: {e}")
        await stop_job_manager()
        return False
    
    # Wait a bit more to ensure job manager processes any pending tasks
    await asyncio.sleep(1)
    
    # Stop job manager
    try:
        await stop_job_manager()
    except Exception as e:
        logger.error(f"❌ Error stopping job manager: {e}")
        return False
    
    return True


async def test_job_listing():
    """Test job listing functionality."""
    logger.info("🧪 Testing job listing...")
    
    # Start job manager
    await start_job_manager()
    
    try:
        # Create a test recommendation
        test_rec = {
            'id': 'test-rec-list',
            'query_hash': 'test_query_hash_list',
            'recommendation_type': 'index',
            'title': 'Test Recommendation for Listing',
            'description': 'Test recommendation for listing testing.',
            'sql_fix': 'CREATE INDEX idx_test_list ON test_table(column3);',
            'original_sql': 'SELECT * FROM test_table WHERE column3 = $1',
            'patch_sql': 'SELECT * FROM test_table WHERE column3 = $1',
            'execution_plan_json': {'extracted_tables': ['test_table']},
            'estimated_improvement_percent': 80,
            'confidence_score': 90,
            'risk_level': 'low',
            'status': 'pending'
        }
        
        rec_id = RecommendationsDB.store_recommendation(test_rec)
        logger.info(f"✅ Created test recommendation: {rec_id}")
        
        # Submit multiple jobs
        job_ids = []
        for i in range(3):
            job_id = await submit_job(rec_id, 'benchmark')
            job_ids.append(job_id)
            logger.info(f"✅ Submitted job {i+1}: {job_id}")
        
        # List all jobs
        all_jobs = await list_jobs()
        logger.info(f"✅ Listed {len(all_jobs)} jobs")
        
        # List pending jobs
        pending_jobs = await list_jobs(status='pending')
        logger.info(f"✅ Listed {len(pending_jobs)} pending jobs")
        
        # List completed jobs
        completed_jobs = await list_jobs(status='completed')
        logger.info(f"✅ Listed {len(completed_jobs)} completed jobs")
        
        # Wait for jobs to complete
        await asyncio.sleep(5)
        
        # Check final counts
        final_jobs = await list_jobs()
        completed_final = await list_jobs(status='completed')
        
        logger.info(f"✅ Final job count: {len(final_jobs)}")
        logger.info(f"✅ Final completed count: {len(completed_final)}")
        
        return True
        
    finally:
        # Stop job manager
        await stop_job_manager()


async def test_apply_and_rollback_jobs():
    """Test apply and rollback job types."""
    logger.info("🧪 Testing apply and rollback jobs...")
    
    # Start job manager
    await start_job_manager()
    
    try:
        # Create a test recommendation
        test_rec = {
            'id': 'test-rec-apply',
            'query_hash': 'test_query_hash_apply',
            'recommendation_type': 'index',
            'title': 'Test Recommendation for Apply',
            'description': 'Test recommendation for apply testing.',
            'sql_fix': 'CREATE INDEX idx_test_apply ON test_table(column4);',
            'original_sql': 'SELECT * FROM test_table WHERE column4 = $1',
            'patch_sql': 'SELECT * FROM test_table WHERE column4 = $1',
            'execution_plan_json': {'extracted_tables': ['test_table']},
            'estimated_improvement_percent': 70,
            'confidence_score': 80,
            'risk_level': 'low',
            'status': 'pending'
        }
        
        rec_id = RecommendationsDB.store_recommendation(test_rec)
        logger.info(f"✅ Created test recommendation: {rec_id}")
        
        # Submit apply job
        apply_job_id = await submit_job(rec_id, 'apply')
        logger.info(f"✅ Submitted apply job: {apply_job_id}")
        
        # Wait for apply job to complete
        await asyncio.sleep(3)
        
        apply_job = await get_job_status(apply_job_id)
        logger.info(f"✅ Apply job status: {apply_job['status']}")
        
        if apply_job['status'] == 'completed':
            logger.info("✅ Apply job completed successfully")
        else:
            logger.error(f"❌ Apply job failed: {apply_job.get('error_message', 'Unknown error')}")
            return False
        
        # Submit rollback job
        rollback_job_id = await submit_job(rec_id, 'rollback')
        logger.info(f"✅ Submitted rollback job: {rollback_job_id}")
        
        # Wait for rollback job to complete
        await asyncio.sleep(3)
        
        rollback_job = await get_job_status(rollback_job_id)
        logger.info(f"✅ Rollback job status: {rollback_job['status']}")
        
        if rollback_job['status'] == 'completed':
            logger.info("✅ Rollback job completed successfully")
        else:
            logger.error(f"❌ Rollback job failed: {rollback_job.get('error_message', 'Unknown error')}")
            return False
        
        return True
        
    finally:
        # Stop job manager
        await stop_job_manager()


async def cleanup_test_data():
    """Clean up test data."""
    logger.info("🧹 Cleaning up test data...")
    
    # Clear all data
    RecommendationsDB.clear_all_recommendations()
    BenchmarkJobsDB.clear_all_jobs()
    
    logger.info("✅ Test data cleaned up")


async def main():
    """Run all Phase 3 tests."""
    logger.info("🚀 Starting Phase 3 simple tests...")
    
    try:
        # Run tests
        tests = [
            ("Job Manager Lifecycle", test_job_manager_lifecycle),
            ("Job Submission", test_job_submission),
            ("Job Cancellation", test_job_cancellation),
            ("Job Listing", test_job_listing),
            ("Apply and Rollback Jobs", test_apply_and_rollback_jobs)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                if await test_func():
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
            logger.info("🎉 All tests passed! Phase 3 implementation is working correctly.")
        else:
            logger.error(f"⚠️  {total - passed} tests failed. Please check the implementation.")
        
        # Cleanup
        await cleanup_test_data()
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return False
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 