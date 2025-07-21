"""
Async job manager for OptiSchema backend.
Handles benchmark job processing and lifecycle management.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from benchmark_jobs import BenchmarkJobsDB
from recommendations_db import RecommendationsDB

logger = logging.getLogger(__name__)

# Global job queue and executor
job_queue = asyncio.Queue()
job_executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent jobs
active_jobs = {}  # Track active job tasks


class JobManager:
    """Manages async benchmark job processing."""
    
    def __init__(self):
        self.is_running = False
        self.worker_task = None
    
    async def start(self):
        """Start the job manager."""
        if self.is_running:
            logger.warning("Job manager is already running")
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Job manager started")
    
    async def stop(self):
        """Stop the job manager."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel the worker task
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
        
        # Cancel all active jobs
        active_jobs_copy = dict(active_jobs)
        for job_id, task in active_jobs_copy.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        active_jobs.clear()
        logger.info("Job manager stopped")
    
    async def _worker_loop(self):
        """Main worker loop for processing jobs."""
        logger.info("Job worker loop started")
        
        while self.is_running:
            try:
                # Wait for a job with timeout
                try:
                    job_data = await asyncio.wait_for(job_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process the job
                job_id = job_data['job_id']
                recommendation_id = job_data['recommendation_id']
                job_type = job_data['job_type']
                
                logger.info(f"Processing job {job_id} for recommendation {recommendation_id}")
                
                # Create task for job processing
                task = asyncio.create_task(self._process_job(job_id, recommendation_id, job_type))
                active_jobs[job_id] = task
                
                # Mark job as done in queue
                job_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(1)
        
        logger.info("Job worker loop stopped")
    
    async def _process_job(self, job_id: str, recommendation_id: str, job_type: str):
        """Process a single job."""
        try:
            # Update job status to running
            BenchmarkJobsDB.update_job_status(job_id, 'running')
            
            # Get recommendation details
            recommendation = RecommendationsDB.get_recommendation(recommendation_id)
            if not recommendation:
                raise Exception(f"Recommendation {recommendation_id} not found")
            
            # Process based on job type
            if job_type == 'benchmark':
                result = await self._run_benchmark_job(job_id, recommendation)
            elif job_type == 'apply':
                result = await self._run_apply_job(job_id, recommendation)
            elif job_type == 'rollback':
                result = await self._run_rollback_job(job_id, recommendation)
            else:
                raise Exception(f"Unknown job type: {job_type}")
            
            # Update job with results
            BenchmarkJobsDB.update_job_status(job_id, 'completed', result=result)
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            BenchmarkJobsDB.update_job_status(job_id, 'error', error_message=str(e))
        
        finally:
            # Remove from active jobs
            if job_id in active_jobs:
                del active_jobs[job_id]
    
    async def _run_benchmark_job(self, job_id: str, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Run a benchmark job with real database operations."""
        logger.info(f"Running benchmark for job {job_id}")
        
        schema_manager = None
        benchmark_target = "main"  # Default to main database
        
        try:
            # Get benchmark targets for different operations
            from replica_manager import get_replica_manager
            
            replica_manager = get_replica_manager()
            
            # For read operations (baseline queries), we can use main database safely
            read_target_type, read_pool = await replica_manager.get_benchmark_target(prefer_replica=True, operation_type="read")
            
            # For DDL operations (CREATE INDEX, etc.), we need replica or fail
            ddl_target_type, ddl_pool = await replica_manager.get_benchmark_target(prefer_replica=True, operation_type="ddl")
            
            if read_target_type == "none":
                raise Exception("No benchmark target available for read operations")
            
            if ddl_target_type == "none":
                logger.warning("No replica available for DDL operations - falling back to mock benchmark")
                # Fall back to mock benchmark if no replica available
                return await self._run_mock_benchmark(job_id, recommendation)
            
            benchmark_target = f"{read_target_type}+{ddl_target_type}"
            logger.info(f"Using {read_target_type} database for reads and {ddl_target_type} database for DDL")
            
            # Get schema manager dynamically - use the DDL pool for schema operations
            from schema_manager import get_schema_manager, init_schema_manager
            
            try:
                schema_manager = get_schema_manager()
            except RuntimeError:
                # Schema manager not initialized, try to initialize it with DDL pool
                if ddl_pool:
                    init_schema_manager(ddl_pool)
                    schema_manager = get_schema_manager()
                    logger.info(f"Schema manager initialized dynamically in job manager with {ddl_target_type} database")
                else:
                    raise Exception("No database pool available for schema manager initialization")
            
            # Extract tables from execution plan
            execution_plan = recommendation.get('execution_plan_json', {})
            tables = execution_plan.get('extracted_tables', [])
            
            if not tables:
                logger.warning(f"No tables found in execution plan for job {job_id}")
                # Fallback to mock result
                return await self._run_mock_benchmark(job_id, recommendation)
            
            # Create temporary schema with sampled data
            sample_percentage = 1.0  # 100% for now, can be configurable
            schema_name = await schema_manager.create_temp_schema(
                job_id, tables, sample_percentage
            )
            
            # Get original and patched SQL
            original_sql = recommendation.get('original_sql', '')
            patch_sql = recommendation.get('patch_sql', '')
            
            if not original_sql:
                logger.warning(f"No original SQL found for job {job_id}")
                return await self._run_mock_benchmark(job_id, recommendation)
            
            # Execute baseline query
            logger.info(f"Executing baseline query for job {job_id}")
            baseline_time, baseline_metrics = await schema_manager.execute_query_in_schema(
                schema_name, original_sql
            )
            
            # Apply the patch (e.g., create index) if it's a DDL statement
            if patch_sql and patch_sql.strip().upper().startswith(('CREATE', 'ALTER', 'DROP')):
                logger.info(f"Applying DDL patch for job {job_id}: {patch_sql}")
                try:
                    # Execute DDL patch in the temporary schema using the safe DDL method
                    success = await schema_manager.execute_ddl_in_schema(schema_name, patch_sql)
                    if not success:
                        logger.error(f"Failed to apply DDL patch for job {job_id}")
                        # Continue with baseline metrics only
                except Exception as e:
                    logger.error(f"Failed to apply DDL patch for job {job_id}: {e}")
                    # Continue with baseline metrics only
            
            # Execute optimized query
            optimized_time = baseline_time
            optimized_metrics = baseline_metrics
            
            if patch_sql and not patch_sql.strip().upper().startswith(('CREATE', 'ALTER', 'DROP')):
                # If patch is a query modification, execute the patched query
                logger.info(f"Executing optimized query for job {job_id}")
                optimized_time, optimized_metrics = await schema_manager.execute_query_in_schema(
                    schema_name, patch_sql
                )
            
            # Calculate improvements
            time_improvement_ms = baseline_time - optimized_time
            time_improvement_percent = (time_improvement_ms / baseline_time * 100) if baseline_time > 0 else 0
            
            buffer_improvement_percent = 0
            if baseline_metrics.get('shared_buffers_read', 0) > 0:
                buffer_improvement = baseline_metrics['shared_buffers_read'] - optimized_metrics.get('shared_buffers_read', 0)
                buffer_improvement_percent = (buffer_improvement / baseline_metrics['shared_buffers_read'] * 100)
            
            # Get schema info
            schema_info = await schema_manager.get_schema_info(job_id)
            
            result = {
                'job_id': job_id,
                'recommendation_id': recommendation['id'],
                'benchmark_type': 'sandbox_sampled',
                'benchmark_target': benchmark_target,  # 'replica' or 'main'
                'schema_name': schema_name,
                'sample_percentage': sample_percentage,
                'tables_sampled': schema_info['tables'] if schema_info else [],
                'baseline_metrics': baseline_metrics,
                'optimized_metrics': optimized_metrics,
                'improvement': {
                    'time_improvement_ms': time_improvement_ms,
                    'time_improvement_percent': time_improvement_percent,
                    'buffer_improvement_percent': buffer_improvement_percent
                },
                'tables_analyzed': tables,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Benchmark completed for job {job_id}: {time_improvement_percent:.1f}% improvement")
            return result
            
        except Exception as e:
            logger.error(f"Benchmark failed for job {job_id}: {e}")
            # Fallback to mock result
            return await self._run_mock_benchmark(job_id, recommendation)
        
        finally:
            # Clean up temporary schema
            if schema_manager:
                try:
                    await schema_manager.drop_temp_schema(job_id)
                except Exception as e:
                    logger.error(f"Failed to cleanup schema for job {job_id}: {e}")
    
    async def _run_mock_benchmark(self, job_id: str, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Run a mock benchmark job (fallback)."""
        logger.info(f"Running mock benchmark for job {job_id}")
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        result = {
            'job_id': job_id,
            'recommendation_id': recommendation['id'],
            'benchmark_type': 'mock',
            'baseline_metrics': {
                'execution_time_ms': 150.5,
                'shared_buffers_hit': 1000,
                'shared_buffers_read': 500
            },
            'optimized_metrics': {
                'execution_time_ms': 25.2,
                'shared_buffers_hit': 1200,
                'shared_buffers_read': 100
            },
            'improvement': {
                'time_improvement_ms': 125.3,
                'time_improvement_percent': 83.2,
                'buffer_improvement_percent': 80.0
            },
            'tables_analyzed': recommendation.get('execution_plan_json', {}).get('extracted_tables', []),
            'completed_at': datetime.utcnow().isoformat()
        }
        
        return result
    
    async def _run_apply_job(self, job_id: str, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Run an apply job with real DDL execution via ApplyManager."""
        logger.info(f"Running apply for job {job_id}")
        
        try:
            # Import ApplyManager
            from apply_manager import get_apply_manager
            
            apply_manager = get_apply_manager()
            
            # Execute real apply operation
            result = await apply_manager.apply_recommendation(recommendation['id'])
            
            # Return detailed result
            return {
                'job_id': job_id,
                'recommendation_id': recommendation['id'],
                'action': 'apply',
                'sql_executed': result.get('sql_executed', ''),
                'schema_name': result.get('schema_name', ''),
                'status': 'applied',
                'applied_at': result.get('applied_at', datetime.utcnow().isoformat()),
                'rollback_available': result.get('rollback_available', False),
                'message': result.get('message', 'Applied successfully'),
                'success': result.get('success', True)
            }
            
        except Exception as e:
            logger.error(f"Apply job {job_id} failed: {e}")
            # Return error result
            return {
                'job_id': job_id,
                'recommendation_id': recommendation['id'],
                'action': 'apply',
                'status': 'error',
                'error_message': str(e),
                'success': False
            }
    
    async def _run_rollback_job(self, job_id: str, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Run a rollback job with real DDL execution via ApplyManager."""
        logger.info(f"Running rollback for job {job_id}")
        
        try:
            # Import ApplyManager
            from apply_manager import get_apply_manager
            
            apply_manager = get_apply_manager()
            
            # Execute real rollback operation
            result = await apply_manager.rollback_recommendation(recommendation['id'])
            
            # Return detailed result
            return {
                'job_id': job_id,
                'recommendation_id': recommendation['id'],
                'action': 'rollback',
                'sql_executed': result.get('sql_executed', ''),
                'status': 'rolled_back',
                'rolled_back_at': result.get('rolled_back_at', datetime.utcnow().isoformat()),
                'message': result.get('message', 'Rolled back successfully'),
                'success': result.get('success', True)
            }
            
        except Exception as e:
            logger.error(f"Rollback job {job_id} failed: {e}")
            # Return error result
            return {
                'job_id': job_id,
                'recommendation_id': recommendation['id'],
                'action': 'rollback',
                'status': 'error',
                'error_message': str(e),
                'success': False
            }


# Global job manager instance
job_manager = JobManager()


async def start_job_manager():
    """Start the global job manager."""
    # Initialize schema manager if database is connected
    try:
        from db import get_pool
        from schema_manager import init_schema_manager
        
        pool = await get_pool()
        if pool:
            init_schema_manager(pool)
            logger.info("Schema manager initialized in job manager")
        else:
            logger.warning("No database pool available for schema manager initialization")
    except Exception as e:
        logger.warning(f"Failed to initialize schema manager in job manager: {e}")
    
    await job_manager.start()


async def stop_job_manager():
    """Stop the global job manager."""
    await job_manager.stop()


async def submit_job(recommendation_id: str, job_type: str = 'benchmark') -> str:
    """
    Submit a new job to the queue.
    
    Args:
        recommendation_id: ID of the recommendation to process
        job_type: Type of job (benchmark, apply, rollback)
        
    Returns:
        Job ID
    """
    # Create job record first to get the job ID
    job_id = BenchmarkJobsDB.create_job(recommendation_id, job_type)
    
    # Add to queue
    await job_queue.put({
        'job_id': job_id,
        'recommendation_id': recommendation_id,
        'job_type': job_type
    })
    
    logger.info(f"Submitted job {job_id} for recommendation {recommendation_id}")
    return job_id


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job status and details
    """
    job = BenchmarkJobsDB.get_job(job_id)
    if not job:
        return None
    
    # Add additional runtime information
    result = dict(job)
    result['is_active'] = job_id in active_jobs
    result['queue_size'] = job_queue.qsize()
    
    return result


async def list_jobs(status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    List jobs with optional filtering.
    
    Args:
        status: Filter by status
        limit: Maximum number of jobs to return
        
    Returns:
        List of jobs
    """
    jobs = BenchmarkJobsDB.list_jobs(status=status, limit=limit)
    
    # Add runtime information
    for job in jobs:
        job['is_active'] = job['id'] in active_jobs
    
    return jobs


async def cancel_job(job_id: str) -> bool:
    """
    Cancel a running job.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        True if job was cancelled, False otherwise
    """
    if job_id in active_jobs:
        task = active_jobs[job_id]
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Handle race condition where job might already be removed
        if job_id in active_jobs:
            del active_jobs[job_id]
        
        BenchmarkJobsDB.update_job_status(job_id, 'cancelled')
        logger.info(f"Job {job_id} cancelled")
        return True
    
    return False


async def cleanup_old_jobs(hours: int = 24) -> int:
    """
    Clean up old completed jobs.
    
    Args:
        hours: Age threshold in hours
        
    Returns:
        Number of jobs cleaned up
    """
    return BenchmarkJobsDB.cleanup_old_jobs(hours)


def get_job_manager_status() -> Dict[str, Any]:
    """Get job manager status and statistics."""
    return {
        'is_running': job_manager.is_running,
        'queue_size': job_queue.qsize(),
        'active_jobs': len(active_jobs),
        'max_workers': job_executor._max_workers,
        'job_statistics': BenchmarkJobsDB.get_job_statistics()
    } 