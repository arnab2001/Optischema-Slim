"""
SQLite-based benchmark jobs tracking for OptiSchema backend.
Handles async job lifecycle management for benchmark operations.
"""

import sqlite3
import json
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BenchmarkJobsDB:
    """SQLite-based benchmark jobs tracking service"""
    
    DB_PATH = Path("/tmp/optischema_recommendations.db")  # Same database as recommendations
    
    # Ensure thread safety
    _lock = threading.Lock()
    
    @classmethod
    def _init_db(cls):
        """Initialize SQLite database and create tables"""
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Create benchmark_jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmark_jobs (
                    id TEXT PRIMARY KEY,
                    recommendation_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    job_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result_json TEXT,
                    error_message TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_job_id ON benchmark_jobs(recommendation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_status ON benchmark_jobs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_created_at ON benchmark_jobs(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_job_type ON benchmark_jobs(job_type)')
            
            conn.commit()
            conn.close()
    
    @classmethod
    def create_job(cls, recommendation_id: str, job_type: str = "benchmark") -> str:
        """Create a new benchmark job"""
        cls._init_db()
        
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO benchmark_jobs (
                    id, recommendation_id, status, job_type, created_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (job_id, recommendation_id, 'pending', job_type, created_at))
            
            conn.commit()
            conn.close()
        
        logger.info(f"Created benchmark job {job_id} for recommendation {recommendation_id}")
        return job_id
    
    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM benchmark_jobs WHERE id = ?
            ''', (job_id,))
            
            row = cursor.fetchone()
            conn.close()
        
        if row:
            return cls._row_to_dict(row)
        return None
    
    @classmethod
    def update_job_status(cls, job_id: str, status: str, result: Dict[str, Any] = None, error_message: str = None) -> bool:
        """Update job status and results"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Determine timestamp based on status
            timestamp = datetime.utcnow().isoformat()
            if status == 'running':
                started_at = timestamp
                completed_at = None
            elif status in ['completed', 'failed', 'error']:
                started_at = None
                completed_at = timestamp
            else:
                started_at = None
                completed_at = None
            
            cursor.execute('''
                UPDATE benchmark_jobs 
                SET status = ?, 
                    started_at = COALESCE(?, started_at),
                    completed_at = COALESCE(?, completed_at),
                    result_json = ?,
                    error_message = ?
                WHERE id = ?
            ''', (
                status,
                started_at,
                completed_at,
                json.dumps(result) if result else None,
                error_message,
                job_id
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
        
        if success:
            logger.info(f"Updated benchmark job {job_id} status to {status}")
        return success
    
    @classmethod
    def list_jobs(cls, status: str = None, recommendation_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List benchmark jobs with optional filtering"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            query = 'SELECT * FROM benchmark_jobs WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if recommendation_id:
                query += ' AND recommendation_id = ?'
                params.append(recommendation_id)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
        
        return [cls._row_to_dict(row) for row in rows]
    
    @classmethod
    def get_jobs_by_recommendation(cls, recommendation_id: str) -> List[Dict[str, Any]]:
        """Get all jobs for a specific recommendation"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM benchmark_jobs 
                WHERE recommendation_id = ? 
                ORDER BY created_at DESC
            ''', (recommendation_id,))
            
            rows = cursor.fetchall()
            conn.close()
        
        return [cls._row_to_dict(row) for row in rows]
    
    @classmethod
    def get_jobs_count(cls, status: str = None) -> int:
        """Get count of benchmark jobs"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            if status:
                cursor.execute('SELECT COUNT(*) FROM benchmark_jobs WHERE status = ?', (status,))
            else:
                cursor.execute('SELECT COUNT(*) FROM benchmark_jobs')
            
            count = cursor.fetchone()[0]
            conn.close()
        
        return count
    
    @classmethod
    def cleanup_old_jobs(cls, hours: int = 24) -> int:
        """Clean up old completed/failed jobs"""
        cls._init_db()
        
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff_time).isoformat()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM benchmark_jobs 
                WHERE status IN ('completed', 'failed', 'error') 
                AND created_at < ?
            ''', (cutoff_iso,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old benchmark jobs")
        return deleted_count
    
    @classmethod
    def get_job_statistics(cls) -> Dict[str, Any]:
        """Get benchmark job statistics"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM benchmark_jobs')
            total_count = cursor.fetchone()[0]
            
            # Get status distribution
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM benchmark_jobs 
                GROUP BY status
            ''')
            status_distribution = dict(cursor.fetchall())
            
            # Get recent activity
            cursor.execute('''
                SELECT created_at 
                FROM benchmark_jobs 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            last_activity = cursor.fetchone()
            
            # Get average completion time for completed jobs
            cursor.execute('''
                SELECT AVG(
                    (julianday(completed_at) - julianday(started_at)) * 24 * 60 * 60
                ) as avg_duration_seconds
                FROM benchmark_jobs 
                WHERE status = 'completed' 
                AND started_at IS NOT NULL 
                AND completed_at IS NOT NULL
            ''')
            avg_duration = cursor.fetchone()[0]
            
            conn.close()
        
        return {
            'total_jobs': total_count,
            'status_distribution': status_distribution,
            'last_activity': last_activity[0] if last_activity else None,
            'average_duration_seconds': avg_duration if avg_duration else 0
        }
    
    @classmethod
    def _row_to_dict(cls, row: tuple) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        columns = [
            'id', 'recommendation_id', 'status', 'job_type', 'created_at',
            'started_at', 'completed_at', 'result_json', 'error_message'
        ]
        
        result = dict(zip(columns, row))
        
        # Parse JSON fields
        if result.get('result_json'):
            try:
                result['result_json'] = json.loads(result['result_json'])
            except json.JSONDecodeError:
                result['result_json'] = None
        
        return result
    
    @classmethod
    def delete_job(cls, job_id: str) -> bool:
        """Delete a benchmark job"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM benchmark_jobs WHERE id = ?', (job_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
        
        if success:
            logger.info(f"Deleted benchmark job {job_id}")
        return success
    
    @classmethod
    def clear_all_jobs(cls):
        """Clear all benchmark jobs (for testing)"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM benchmark_jobs')
            
            conn.commit()
            conn.close()
        
        logger.info("Cleared all benchmark jobs") 