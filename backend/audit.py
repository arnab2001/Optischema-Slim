"""
Audit service for OptiSchema backend.
Handles logging of all system actions for compliance and trust.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AuditService:
    """Service for managing audit logs using SQLite for prototyping"""
    
    DB_PATH = Path("/tmp/optischema_audit.db")
    
    @classmethod
    def _init_db(cls):
        """Initialize SQLite database and create tables"""
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                user_id TEXT,
                recommendation_id TEXT,
                query_hash TEXT,
                before_metrics TEXT,
                after_metrics TEXT,
                improvement_percent REAL,
                details TEXT,
                risk_level TEXT,
                status TEXT DEFAULT 'completed',
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_action_type ON audit_logs(action_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)')
        
        conn.commit()
        conn.close()
    
    @classmethod
    def log_action(
        cls,
        action_type: str,
        user_id: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        query_hash: Optional[str] = None,
        before_metrics: Optional[Dict[str, Any]] = None,
        after_metrics: Optional[Dict[str, Any]] = None,
        improvement_percent: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_level: Optional[str] = None,
        status: str = "completed"
    ) -> str:
        """Log an action to the audit trail"""
        cls._init_db()
        
        audit_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Basic deduplication: avoid spamming the same applied event for the same recommendation within a short window
        try:
            if action_type == 'recommendation_applied' and recommendation_id:
                cursor.execute(
                    """
                    SELECT id FROM audit_logs
                    WHERE action_type = ? AND recommendation_id = ?
                      AND created_at >= datetime('now', '-5 minutes')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (action_type, recommendation_id)
                )
                row = cursor.fetchone()
                if row:
                    # Return existing audit id without inserting a duplicate
                    existing_id = row[0]
                    conn.close()
                    logger.info("Skipping duplicate audit log for recommendation_applied within 5 minutes")
                    return existing_id
        except Exception:
            # If dedup check fails, continue with logging rather than crashing
            pass
        
        cursor.execute('''
            INSERT INTO audit_logs (
                id, action_type, user_id, recommendation_id, query_hash,
                before_metrics, after_metrics, improvement_percent, details,
                risk_level, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit_id, action_type, user_id, recommendation_id, query_hash,
            json.dumps(before_metrics) if before_metrics else None,
            json.dumps(after_metrics) if after_metrics else None,
            improvement_percent,
            json.dumps(details) if details else None,
            risk_level, status, created_at
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Audit log created: {action_type} by {user_id}")
        return audit_id
    
    @classmethod
    def get_audit_logs(
        cls,
        action_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs with optional filtering"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            log = dict(row)
            # Parse JSON fields
            if log['before_metrics']:
                log['before_metrics'] = json.loads(log['before_metrics'])
            if log['after_metrics']:
                log['after_metrics'] = json.loads(log['after_metrics'])
            if log['details']:
                log['details'] = json.loads(log['details'])
            logs.append(log)
        
        conn.close()
        return logs
    
    @classmethod
    def get_audit_summary(cls) -> Dict[str, Any]:
        """Get summary statistics of audit logs"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Total logs
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        total_logs = cursor.fetchone()[0]
        
        # Logs by action type
        cursor.execute("""
            SELECT action_type, COUNT(*) as count 
            FROM audit_logs 
            GROUP BY action_type 
            ORDER BY count DESC
        """)
        action_type_counts = dict(cursor.fetchall())
        
        # Logs by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM audit_logs 
            GROUP BY status 
            ORDER BY count DESC
        """)
        status_counts = dict(cursor.fetchall())
        
        # Recent activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM audit_logs 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        recent_activity = cursor.fetchone()[0]
        
        # Average improvement
        cursor.execute("""
            SELECT AVG(improvement_percent) FROM audit_logs 
            WHERE improvement_percent IS NOT NULL
        """)
        avg_improvement = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_logs": total_logs,
            "action_type_counts": action_type_counts,
            "status_counts": status_counts,
            "recent_activity_24h": recent_activity,
            "average_improvement_percent": round(avg_improvement, 2)
        } 