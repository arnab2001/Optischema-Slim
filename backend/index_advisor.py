"""
Index advisor service for OptiSchema backend.
Analyzes pg_stat_user_indexes to identify unused and redundant indexes.
"""

import sqlite3
import json
import uuid
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class IndexAdvisorService:
    """Service for analyzing and recommending index optimizations using SQLite for prototyping"""
    
    DB_PATH = Path("/tmp/optischema_indexes.db")
    
    @classmethod
    def _init_db(cls):
        """Initialize SQLite database and create tables"""
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Create index_recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS index_recommendations (
                id TEXT PRIMARY KEY,
                index_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                schema_name TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                size_pretty TEXT NOT NULL,
                idx_scan INTEGER NOT NULL,
                idx_tup_read INTEGER NOT NULL,
                idx_tup_fetch INTEGER NOT NULL,
                last_used TEXT,
                days_unused INTEGER NOT NULL,
                estimated_savings_mb REAL NOT NULL,
                risk_level TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                sql_fix TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendation_type ON index_recommendations(recommendation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendation_risk ON index_recommendations(risk_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendation_created ON index_recommendations(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendation_table ON index_recommendations(table_name, schema_name)')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    async def analyze_unused_indexes(connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze unused indexes from pg_stat_user_indexes.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            List of unused index recommendations
        """
        try:
            # Handle SSL configuration for RDS
            config = connection_config.copy()
            if config.get('ssl') == 'require':
                config['ssl'] = True
            elif config.get('ssl') == 'prefer':
                config['ssl'] = True
            elif config.get('ssl') == 'disable':
                config['ssl'] = False
            
            # For RDS connections, we often need to disable certificate verification
            if config.get('ssl') and config.get('ssl') is not False:
                import ssl
                config['ssl'] = ssl.create_default_context()
                config['ssl'].check_hostname = False
                config['ssl'].verify_mode = ssl.CERT_NONE
            
            # Connect to the monitored database
            conn = await asyncpg.connect(**config)
            
            # Query for unused indexes (idx_scan = 0 in last 24 hours)
            query = """
                SELECT 
                    schemaname as schema_name,
                    tablename as table_name,
                    indexname as index_name,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size_pretty,
                    pg_relation_size(indexrelid) as size_bytes,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    last_vacuum,
                    last_autovacuum
                FROM pg_stat_user_indexes 
                WHERE idx_scan = 0
                ORDER BY pg_relation_size(indexrelid) DESC
            """
            
            rows = await conn.fetch(query)
            await conn.close()
            
            recommendations = []
            for row in rows:
                # Calculate days since last use (estimate based on vacuum info)
                last_used = row['last_vacuum'] or row['last_autovacuum']
                days_unused = 30  # Default assumption
                if last_used:
                    days_unused = (datetime.utcnow() - last_used).days
                
                # Calculate estimated savings
                estimated_savings_mb = row['size_bytes'] / (1024 * 1024)
                
                # Determine risk level
                risk_level = "low"
                if estimated_savings_mb > 100:
                    risk_level = "high"
                elif estimated_savings_mb > 10:
                    risk_level = "medium"
                
                # Generate SQL fix
                sql_fix = f"DROP INDEX {row['schema_name']}.{row['index_name']};"
                
                recommendations.append({
                    'index_name': row['index_name'],
                    'table_name': row['table_name'],
                    'schema_name': row['schema_name'],
                    'size_bytes': row['size_bytes'],
                    'size_pretty': row['size_pretty'],
                    'idx_scan': row['idx_scan'],
                    'idx_tup_read': row['idx_tup_read'],
                    'idx_tup_fetch': row['idx_tup_fetch'],
                    'last_used': last_used.isoformat() if last_used else None,
                    'days_unused': days_unused,
                    'estimated_savings_mb': round(estimated_savings_mb, 2),
                    'risk_level': risk_level,
                    'recommendation_type': 'drop',
                    'sql_fix': sql_fix
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to analyze unused indexes: {e}")
            return []
    
    @staticmethod
    async def analyze_redundant_indexes(connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze potentially redundant indexes.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            List of redundant index recommendations
        """
        try:
            # Handle SSL configuration for RDS
            config = connection_config.copy()
            if config.get('ssl') == 'require':
                config['ssl'] = True
            elif config.get('ssl') == 'prefer':
                config['ssl'] = True
            elif config.get('ssl') == 'disable':
                config['ssl'] = False
            
            # For RDS connections, we often need to disable certificate verification
            if config.get('ssl') and config.get('ssl') is not False:
                import ssl
                config['ssl'] = ssl.create_default_context()
                config['ssl'].check_hostname = False
                config['ssl'].verify_mode = ssl.CERT_NONE
            
            # Connect to the monitored database
            conn = await asyncpg.connect(**config)
            
            # Query for potentially redundant indexes
            # This is a simplified analysis - in production you'd want more sophisticated logic
            query = """
                SELECT 
                    schemaname as schema_name,
                    tablename as table_name,
                    indexname as index_name,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size_pretty,
                    pg_relation_size(indexrelid) as size_bytes,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_scan < 10  -- Low usage indexes
                AND pg_relation_size(indexrelid) > 1024 * 1024  -- Larger than 1MB
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 20
            """
            
            rows = await conn.fetch(query)
            await conn.close()
            
            recommendations = []
            for row in rows:
                # Calculate estimated savings
                estimated_savings_mb = row['size_bytes'] / (1024 * 1024)
                
                # Determine risk level based on usage
                risk_level = "medium"
                if row['idx_scan'] == 0:
                    risk_level = "low"
                elif row['idx_scan'] > 5:
                    risk_level = "high"
                
                # Generate SQL fix
                sql_fix = f"DROP INDEX {row['schema_name']}.{row['index_name']};"
                
                recommendations.append({
                    'index_name': row['index_name'],
                    'table_name': row['table_name'],
                    'schema_name': row['schema_name'],
                    'size_bytes': row['size_bytes'],
                    'size_pretty': row['size_pretty'],
                    'idx_scan': row['idx_scan'],
                    'idx_tup_read': row['idx_tup_read'],
                    'idx_tup_fetch': row['idx_tup_fetch'],
                    'last_used': None,  # Would need more complex analysis
                    'days_unused': 0,
                    'estimated_savings_mb': round(estimated_savings_mb, 2),
                    'risk_level': risk_level,
                    'recommendation_type': 'analyze',
                    'sql_fix': sql_fix
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to analyze redundant indexes: {e}")
            return []
    
    @classmethod
    def store_index_recommendations(cls, recommendations: List[Dict[str, Any]]) -> List[str]:
        """Store index recommendations in SQLite"""
        cls._init_db()
        
        recommendation_ids = []
        created_at = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        for rec in recommendations:
            rec_id = str(uuid.uuid4())
            recommendation_ids.append(rec_id)
            
            cursor.execute('''
                INSERT INTO index_recommendations (
                    id, index_name, table_name, schema_name, size_bytes, size_pretty,
                    idx_scan, idx_tup_read, idx_tup_fetch, last_used, days_unused,
                    estimated_savings_mb, risk_level, recommendation_type, sql_fix, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec_id, rec['index_name'], rec['table_name'], rec['schema_name'],
                rec['size_bytes'], rec['size_pretty'], rec['idx_scan'], rec['idx_tup_read'],
                rec['idx_tup_fetch'], rec['last_used'], rec['days_unused'],
                rec['estimated_savings_mb'], rec['risk_level'], rec['recommendation_type'],
                rec['sql_fix'], created_at
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {len(recommendations)} index recommendations")
        return recommendation_ids
    
    @classmethod
    def get_index_recommendations(
        cls,
        recommendation_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get index recommendations with optional filtering"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM index_recommendations WHERE 1=1"
        params = []
        
        if recommendation_type:
            query += " AND recommendation_type = ?"
            params.append(recommendation_type)
        
        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        recommendations = []
        for row in rows:
            recommendations.append(dict(row))
        
        conn.close()
        return recommendations
    
    @classmethod
    def get_index_recommendation_summary(cls) -> Dict[str, Any]:
        """Get summary statistics of index recommendations"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        # Total recommendations
        cursor.execute("SELECT COUNT(*) FROM index_recommendations")
        total_recommendations = cursor.fetchone()[0]
        
        # Recommendations by type
        cursor.execute("""
            SELECT recommendation_type, COUNT(*) as count 
            FROM index_recommendations 
            GROUP BY recommendation_type
        """)
        type_counts = dict(cursor.fetchall())
        
        # Recommendations by risk level
        cursor.execute("""
            SELECT risk_level, COUNT(*) as count 
            FROM index_recommendations 
            GROUP BY risk_level
        """)
        risk_counts = dict(cursor.fetchall())
        
        # Total potential savings
        cursor.execute("""
            SELECT SUM(estimated_savings_mb) FROM index_recommendations
        """)
        total_savings = cursor.fetchone()[0] or 0
        
        # Recent recommendations (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM index_recommendations 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        recent_recommendations = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_recommendations": total_recommendations,
            "recommendations_by_type": type_counts,
            "recommendations_by_risk": risk_counts,
            "total_potential_savings_mb": round(total_savings, 2),
            "recent_recommendations_24h": recent_recommendations
        }
    
    @classmethod
    def delete_recommendation(cls, recommendation_id: str) -> bool:
        """Delete a specific recommendation"""
        cls._init_db()
        
        conn = sqlite3.connect(str(cls.DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM index_recommendations WHERE id = ?', (recommendation_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"Deleted index recommendation: {recommendation_id}")
        
        return deleted
    
    @staticmethod
    async def get_database_index_stats(connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get database index statistics to understand what indexes exist.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            Dictionary with index statistics
        """
        try:
            # Handle SSL configuration for RDS
            config = connection_config.copy()
            if config.get('ssl') == 'require':
                config['ssl'] = True
            elif config.get('ssl') == 'prefer':
                config['ssl'] = True
            elif config.get('ssl') == 'disable':
                config['ssl'] = False
            
            # For RDS connections, we often need to disable certificate verification
            if config.get('ssl') and config.get('ssl') is not False:
                import ssl
                config['ssl'] = ssl.create_default_context()
                config['ssl'].check_hostname = False
                config['ssl'].verify_mode = ssl.CERT_NONE
            
            conn = await asyncpg.connect(**config)
            
            # Get total number of user indexes
            total_indexes_query = """
                SELECT COUNT(*) as total_indexes
                FROM pg_stat_user_indexes
            """
            
            # Get indexes by usage
            usage_stats_query = """
                SELECT 
                    CASE 
                        WHEN idx_scan = 0 THEN 'unused'
                        WHEN idx_scan < 10 THEN 'low_usage'
                        WHEN idx_scan < 100 THEN 'medium_usage'
                        ELSE 'high_usage'
                    END as usage_category,
                    COUNT(*) as count,
                    SUM(pg_relation_size(indexrelid)) as total_size_bytes
                FROM pg_stat_user_indexes
                GROUP BY 
                    CASE 
                        WHEN idx_scan = 0 THEN 'unused'
                        WHEN idx_scan < 10 THEN 'low_usage'
                        WHEN idx_scan < 100 THEN 'medium_usage'
                        ELSE 'high_usage'
                    END
                ORDER BY usage_category
            """
            
            # Get largest indexes
            largest_indexes_query = """
                SELECT 
                    schemaname as schema_name,
                    tablename as table_name,
                    indexname as index_name,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size_pretty,
                    pg_relation_size(indexrelid) as size_bytes,
                    idx_scan
                FROM pg_stat_user_indexes
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 10
            """
            
            total_result = await conn.fetchrow(total_indexes_query)
            usage_results = await conn.fetch(usage_stats_query)
            largest_results = await conn.fetch(largest_indexes_query)
            
            await conn.close()
            
            # Process usage stats
            usage_stats = {}
            for row in usage_results:
                usage_stats[row['usage_category']] = {
                    'count': row['count'],
                    'total_size_mb': round(row['total_size_bytes'] / (1024 * 1024), 2)
                }
            
            # Process largest indexes
            largest_indexes = []
            for row in largest_results:
                largest_indexes.append({
                    'schema_name': row['schema_name'],
                    'table_name': row['table_name'],
                    'index_name': row['index_name'],
                    'size_pretty': row['size_pretty'],
                    'size_bytes': row['size_bytes'],
                    'idx_scan': row['idx_scan']
                })
            
            return {
                "total_indexes": total_result['total_indexes'],
                "usage_stats": usage_stats,
                "largest_indexes": largest_indexes
            }
            
        except Exception as e:
            logger.error(f"Failed to get database index stats: {e}")
            return {
                "total_indexes": 0,
                "usage_stats": {},
                "largest_indexes": [],
                "error": str(e)
            }

    @staticmethod
    async def run_full_analysis(connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run full index analysis and store recommendations.
        
        Args:
            connection_config: Database connection configuration
            
        Returns:
            Analysis results summary
        """
        try:
            # Get database index statistics first
            index_stats = await IndexAdvisorService.get_database_index_stats(connection_config)
            
            # Analyze unused indexes
            unused_indexes = await IndexAdvisorService.analyze_unused_indexes(connection_config)
            
            # Analyze redundant indexes
            redundant_indexes = await IndexAdvisorService.analyze_redundant_indexes(connection_config)
            
            # Combine all recommendations
            all_recommendations = unused_indexes + redundant_indexes
            
            # Store recommendations
            if all_recommendations:
                recommendation_ids = IndexAdvisorService.store_index_recommendations(all_recommendations)
            else:
                recommendation_ids = []
            
            # Calculate summary
            total_savings = sum(rec['estimated_savings_mb'] for rec in all_recommendations)
            
            return {
                "success": True,
                "total_recommendations": len(all_recommendations),
                "unused_indexes": len(unused_indexes),
                "redundant_indexes": len(redundant_indexes),
                "total_potential_savings_mb": round(total_savings, 2),
                "recommendation_ids": recommendation_ids,
                "analyzed_at": datetime.utcnow().isoformat(),
                "database_stats": index_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to run full index analysis: {e}")
            return {
                "success": False,
                "error": str(e)
            } 