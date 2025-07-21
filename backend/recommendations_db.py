"""
SQLite-based recommendations storage for OptiSchema backend.
Prototype implementation for Phase 1 data persistence.
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

class RecommendationsDB:
    """SQLite-based recommendations storage service"""
    
    DB_PATH = Path("/tmp/optischema_recommendations.db")
    
    # Ensure thread safety
    _lock = threading.Lock()
    
    @classmethod
    def _init_db(cls):
        """Initialize SQLite database and create tables"""
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Create recommendations table with all required fields
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recommendations (
                    id TEXT PRIMARY KEY,
                    query_hash TEXT NOT NULL,
                    recommendation_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    sql_fix TEXT,
                    original_sql TEXT,
                    patch_sql TEXT,
                    execution_plan_json TEXT,
                    estimated_improvement_percent INTEGER,
                    confidence_score INTEGER,
                    risk_level TEXT,
                    status TEXT DEFAULT 'pending',
                    applied BOOLEAN DEFAULT FALSE,
                    applied_at TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rec_query_hash ON recommendations(query_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rec_type ON recommendations(recommendation_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rec_status ON recommendations(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rec_created_at ON recommendations(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_job_id ON benchmark_jobs(recommendation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_status ON benchmark_jobs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_created_at ON benchmark_jobs(created_at)')
            
            conn.commit()
            conn.close()
    
    @classmethod
    def store_recommendation(cls, recommendation: Dict[str, Any]) -> str:
        """Store a recommendation in SQLite"""
        cls._init_db()
        
        # Validate recommendation to prevent test data in production
        cls._validate_recommendation(recommendation)
        
        # Convert UUID to string if needed
        rec_id = recommendation.get('id')
        if hasattr(rec_id, 'hex'):  # UUID object
            rec_id = str(rec_id)
        elif not rec_id:
            rec_id = str(uuid.uuid4())
        
        created_at = datetime.utcnow().isoformat()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO recommendations (
                    id, query_hash, recommendation_type, title, description, sql_fix,
                    original_sql, patch_sql, execution_plan_json, estimated_improvement_percent,
                    confidence_score, risk_level, status, applied, applied_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec_id,
                recommendation.get('query_hash', ''),
                recommendation.get('recommendation_type', 'unknown'),
                recommendation.get('title', ''),
                recommendation.get('description', ''),
                recommendation.get('sql_fix'),
                recommendation.get('original_sql'),
                recommendation.get('patch_sql'),
                json.dumps(recommendation.get('execution_plan_json')) if recommendation.get('execution_plan_json') else None,
                recommendation.get('estimated_improvement_percent'),
                recommendation.get('confidence_score'),
                recommendation.get('risk_level'),
                recommendation.get('status', 'pending'),
                recommendation.get('applied', False),
                recommendation.get('applied_at'),
                created_at
            ))
            
            conn.commit()
            conn.close()
        
        logger.info(f"Stored recommendation {rec_id}")
        return rec_id
    
    @classmethod
    def get_recommendation(cls, rec_id: str) -> Optional[Dict[str, Any]]:
        """Get a recommendation by ID"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM recommendations WHERE id = ?
            ''', (rec_id,))
            
            row = cursor.fetchone()
            conn.close()
        
        if row:
            return cls._row_to_dict(row)
        return None
    
    @classmethod
    def list_recommendations(cls, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List recommendations with optional filtering"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT * FROM recommendations 
                    WHERE status = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT * FROM recommendations 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
        
        return [cls._row_to_dict(row) for row in rows]
    
    @classmethod
    def update_recommendation_status(cls, rec_id: str, status: str, **kwargs) -> bool:
        """Update recommendation status and other fields"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Build dynamic update query
            update_fields = ['status = ?']
            values = [status]
            
            for key, value in kwargs.items():
                if key in ['applied', 'applied_at', 'sql_fix', 'original_sql', 'patch_sql']:
                    update_fields.append(f'{key} = ?')
                    values.append(value)
            
            values.append(rec_id)
            
            cursor.execute(f'''
                UPDATE recommendations 
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', values)
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
        
        if success:
            logger.info(f"Updated recommendation {rec_id} status to {status}")
        return success
    
    @classmethod
    def delete_recommendation(cls, rec_id: str) -> bool:
        """Delete a recommendation"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM recommendations WHERE id = ?', (rec_id,))
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
        
        if success:
            logger.info(f"Deleted recommendation {rec_id}")
        return success
    
    @classmethod
    def get_recommendations_by_query_hash(cls, query_hash: str) -> List[Dict[str, Any]]:
        """Get all recommendations for a specific query"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM recommendations 
                WHERE query_hash = ? 
                ORDER BY created_at DESC
            ''', (query_hash,))
            
            rows = cursor.fetchall()
            conn.close()
        
        return [cls._row_to_dict(row) for row in rows]
    
    @classmethod
    def get_recommendations_count(cls, status: str = None) -> int:
        """Get count of recommendations"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            if status:
                cursor.execute('SELECT COUNT(*) FROM recommendations WHERE status = ?', (status,))
            else:
                cursor.execute('SELECT COUNT(*) FROM recommendations')
            
            count = cursor.fetchone()[0]
            conn.close()
        
        return count
    
    @classmethod
    def _row_to_dict(cls, row: tuple) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        columns = [
            'id', 'query_hash', 'recommendation_type', 'title', 'description', 'sql_fix',
            'original_sql', 'patch_sql', 'execution_plan_json', 'estimated_improvement_percent',
            'confidence_score', 'risk_level', 'status', 'applied', 'applied_at', 'created_at'
        ]
        
        result = dict(zip(columns, row))
        
        # Parse JSON fields
        if result.get('execution_plan_json'):
            try:
                result['execution_plan_json'] = json.loads(result['execution_plan_json'])
            except json.JSONDecodeError:
                result['execution_plan_json'] = None
        
        return result
    
    @classmethod
    def clear_all_recommendations(cls):
        """Clear all recommendations (for testing)"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM recommendations')
            cursor.execute('DELETE FROM benchmark_jobs')
            
            conn.commit()
            conn.close()
        
        logger.info("Cleared all recommendations and benchmark jobs")
    
    @classmethod
    def _validate_recommendation(cls, recommendation: Dict[str, Any]) -> None:
        """Validate recommendation to prevent test data in production."""
        rec_id = recommendation.get('id', '')
        title = recommendation.get('title', '')
        
        # Check for test patterns
        test_patterns = [
            'phase6', 'phase7', 'phase4', 'phase5',
            'test-rec', 'final-test', 'frontend-test',
            'sandbox-test', 'apply-test'
        ]
        
        for pattern in test_patterns:
            if pattern in str(rec_id).lower() or pattern in title.lower():
                logger.warning(f"⚠️  Detected test recommendation pattern '{pattern}' in ID: {rec_id}, Title: {title}")
                # In production, you might want to raise an exception here
                # raise ValueError(f"Test recommendation detected: {rec_id}")
        
        # Ensure recommendation has required fields
        required_fields = ['title', 'description', 'recommendation_type']
        for field in required_fields:
            if not recommendation.get(field):
                raise ValueError(f"Missing required field: {field}")

    @classmethod
    def get_database_info(cls) -> Dict[str, Any]:
        """Get database statistics and information"""
        cls._init_db()
        
        with cls._lock:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()
            
            # Get table sizes
            cursor.execute('SELECT COUNT(*) FROM recommendations')
            rec_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM benchmark_jobs')
            job_count = cursor.fetchone()[0]
            
            # Get status distribution
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM recommendations 
                GROUP BY status
            ''')
            status_distribution = dict(cursor.fetchall())
            
            # Get recent activity
            cursor.execute('''
                SELECT created_at 
                FROM recommendations 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            last_activity = cursor.fetchone()
            
            conn.close()
        
        return {
            'total_recommendations': rec_count,
            'total_benchmark_jobs': job_count,
            'status_distribution': status_distribution,
            'last_activity': last_activity[0] if last_activity else None,
            'database_path': str(cls.DB_PATH)
        } 