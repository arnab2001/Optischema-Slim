"""
Connection baseline service for OptiSchema backend.
Handles measurement and storage of network latency baselines for multi-database connections.
"""

import sqlite3
import json
import uuid
import asyncio
import asyncpg
import ssl
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConnectionBaselineService:
    """Service for managing connection latency baselines using SQLite for prototyping"""
    
    DB_PATH = Path("/tmp/optischema_baselines.db")
    
    @classmethod
    def _init_db(cls):
        """Initialize SQLite database and create tables"""
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Create connection_baselines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_baselines (
                id TEXT PRIMARY KEY,
                connection_id TEXT UNIQUE NOT NULL,
                connection_name TEXT NOT NULL,
                baseline_latency_ms REAL NOT NULL,
                measured_at TEXT NOT NULL,
                connection_config TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_baseline_connection_id ON connection_baselines(connection_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_baseline_active ON connection_baselines(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_baseline_measured_at ON connection_baselines(measured_at)')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    async def measure_connection_latency(connection_config: Dict[str, Any]) -> float:
        """
        Measure Round-Trip Time (RTT) latency to a PostgreSQL database.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            Latency in milliseconds
        """
        start_time = datetime.utcnow()
        
        try:
            # Prepare connection config with SSL settings
            config = connection_config.copy()
            
            # Add SSL configuration if not present
            if 'ssl' not in config:
                config['ssl'] = 'require'  # Default to require SSL for RDS
            
            # Handle different SSL modes
            if config.get('ssl') == 'require':
                config['ssl'] = True
            elif config.get('ssl') == 'prefer':
                config['ssl'] = True
            elif config.get('ssl') == 'disable':
                config['ssl'] = False
            
            # For RDS connections, we often need to disable certificate verification
            # due to self-signed certificates in the chain
            if config.get('ssl') and config.get('ssl') is not False:
                import ssl
                config['ssl'] = ssl.create_default_context()
                config['ssl'].check_hostname = False
                config['ssl'].verify_mode = ssl.CERT_NONE
            
            # Connect and execute a simple query
            conn = await asyncpg.connect(**config)
            try:
                await conn.execute('SELECT 1')
            finally:
                await conn.close()
            
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Connection latency measured: {latency_ms:.2f}ms")
            return latency_ms
            
        except Exception as e:
            logger.error(f"Failed to measure connection latency: {e}")
            raise
    
    @classmethod
    def store_baseline(
        cls,
        connection_id: str,
        connection_name: str,
        baseline_latency_ms: float,
        connection_config: Dict[str, Any]
    ) -> str:
        """Store a connection baseline in SQLite"""
        cls._init_db()
        
        baseline_id = str(uuid.uuid4())
        measured_at = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Deactivate existing baseline for this connection
        cursor.execute('''
            UPDATE connection_baselines 
            SET is_active = 0 
            WHERE connection_id = ?
        ''', (connection_id,))
        
        # Insert new baseline; if unique conflict on connection_id, update existing row
        try:
            cursor.execute('''
                INSERT INTO connection_baselines (
                    id, connection_id, connection_name, baseline_latency_ms,
                    measured_at, connection_config, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (
                baseline_id, connection_id, connection_name, baseline_latency_ms,
                measured_at, json.dumps(connection_config)
            ))
        except sqlite3.IntegrityError:
            # Update existing active row
            cursor.execute('''
                UPDATE connection_baselines 
                SET connection_name = ?, baseline_latency_ms = ?, measured_at = ?, connection_config = ?, is_active = 1
                WHERE connection_id = ?
            ''', (
                connection_name, baseline_latency_ms, measured_at, json.dumps(connection_config), connection_id
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Connection baseline stored: {connection_name} - {baseline_latency_ms:.2f}ms")
        return baseline_id
    
    @classmethod
    def get_baseline(cls, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get the active baseline for a connection"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM connection_baselines 
            WHERE connection_id = ? AND is_active = 1
            ORDER BY measured_at DESC LIMIT 1
        ''', (connection_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            baseline = dict(row)
            baseline['connection_config'] = json.loads(baseline['connection_config'])
            return baseline
        
        return None
    
    @classmethod
    def get_all_baselines(cls) -> List[Dict[str, Any]]:
        """Get all active connection baselines"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM connection_baselines 
            WHERE is_active = 1
            ORDER BY measured_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        baselines = []
        for row in rows:
            baseline = dict(row)
            baseline['connection_config'] = json.loads(baseline['connection_config'])
            baselines.append(baseline)
        
        return baselines
    
    @classmethod
    def update_baseline(
        cls,
        connection_id: str,
        baseline_latency_ms: float
    ) -> bool:
        """Update an existing baseline"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE connection_baselines 
            SET baseline_latency_ms = ?, measured_at = ?
            WHERE connection_id = ? AND is_active = 1
        ''', (baseline_latency_ms, datetime.utcnow().isoformat(), connection_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if updated:
            logger.info(f"Connection baseline updated: {connection_id} - {baseline_latency_ms:.2f}ms")
        
        return updated
    
    @classmethod
    def deactivate_baseline(cls, connection_id: str) -> bool:
        """Deactivate a connection baseline"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE connection_baselines 
            SET is_active = 0
            WHERE connection_id = ?
        ''', (connection_id,))
        
        deactivated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deactivated:
            logger.info(f"Connection baseline deactivated: {connection_id}")
        
        return deactivated
    
    @classmethod
    def get_baseline_summary(cls) -> Dict[str, Any]:
        """Get summary statistics of connection baselines"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Total active baselines
        cursor.execute("SELECT COUNT(*) FROM connection_baselines WHERE is_active = 1")
        total_baselines = cursor.fetchone()[0]
        
        # Average latency
        cursor.execute("""
            SELECT AVG(baseline_latency_ms) FROM connection_baselines 
            WHERE is_active = 1
        """)
        avg_latency = cursor.fetchone()[0] or 0
        
        # Min/Max latency
        cursor.execute("""
            SELECT MIN(baseline_latency_ms), MAX(baseline_latency_ms) 
            FROM connection_baselines WHERE is_active = 1
        """)
        min_latency, max_latency = cursor.fetchone()
        
        # Recent measurements (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM connection_baselines 
            WHERE measured_at >= datetime('now', '-1 day')
        """)
        recent_measurements = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_active_baselines": total_baselines,
            "average_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min_latency, 2) if min_latency else 0,
            "max_latency_ms": round(max_latency, 2) if max_latency else 0,
            "recent_measurements_24h": recent_measurements
        }
    
    @staticmethod
    async def measure_and_store_baseline(
        connection_config: Dict[str, Any],
        connection_name: str
    ) -> Dict[str, Any]:
        """
        Measure connection latency and store the baseline.
        
        Args:
            connection_config: Database connection configuration
            connection_name: Human-readable connection name
            
        Returns:
            Dictionary with success status and baseline data
        """
        try:
            # Generate connection ID from config hash
            config_hash = str(hash(json.dumps(connection_config, sort_keys=True)))
            connection_id = f"{connection_name}_{config_hash}"
            
            # Measure latency
            latency_ms = await ConnectionBaselineService.measure_connection_latency(connection_config)
            
            # Store baseline
            baseline_id = ConnectionBaselineService.store_baseline(
                connection_id, connection_name, latency_ms, connection_config
            )
            
            return {
                "success": True,
                "baseline_id": baseline_id,
                "connection_id": connection_id,
                "connection_name": connection_name,
                "latency_ms": latency_ms,
                "measured_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to measure and store baseline: {e}")
            return {
                "success": False,
                "error": str(e)
            } 