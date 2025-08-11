import asyncio
import asyncpg
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from contextlib import asynccontextmanager
import logging
import re
import json

from config import settings
from recommendations_db import RecommendationsDB
from sandbox import get_sandbox_connection

logger = logging.getLogger(__name__)


class AuditLogger:
    """Handles immutable audit logging for all DDL operations."""
    
    @staticmethod
    async def log_operation(conn: asyncpg.Connection, operation_type: str, 
                          recommendation_id: str, sql_executed: str, 
                          status: str, details: Dict[str, Any] = None):
        """
        Log an operation to the audit trail.
        
        Args:
            conn: Database connection
            operation_type: 'apply' or 'rollback'
            recommendation_id: ID of recommendation
            sql_executed: SQL that was executed
            status: 'success' or 'error'
            details: Additional details dictionary
        """
        try:
            audit_record = {
                'operation_type': operation_type,
                'recommendation_id': recommendation_id,
                'sql_executed': sql_executed,
                'status': status,
                'timestamp': datetime.utcnow().isoformat(),
                'details': details or {}
            }
            
            # Create audit table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS optischema_audit_log (
                    id SERIAL PRIMARY KEY,
                    operation_type VARCHAR(20) NOT NULL,
                    recommendation_id VARCHAR(255) NOT NULL,
                    sql_executed TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert audit record
            await conn.execute("""
                INSERT INTO optischema_audit_log 
                (operation_type, recommendation_id, sql_executed, status, timestamp, details)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
            operation_type, recommendation_id, sql_executed, 
            status, datetime.fromisoformat(audit_record['timestamp']), 
            json.dumps(details) if details else None)
            
            logger.info(f"Audit log entry created: {operation_type} for {recommendation_id}")
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't fail the operation if audit logging fails


class ApplyManager:
    """Manages applying and rolling back DDL changes safely in sandbox database."""
    
    def __init__(self):
        self._applied_changes: Dict[str, Dict[str, Any]] = {}
        self.audit_logger = AuditLogger()
    
    def _validate_sql_safety(self, sql: str) -> bool:
        """
        Validate that SQL is safe for execution.
        Only allows CREATE INDEX CONCURRENTLY, DROP INDEX CONCURRENTLY, ALTER SYSTEM, SET commands.
        """
        if not sql or not sql.strip():
            return False
        
        sql_upper = sql.strip().upper()
        
        # Allow CREATE INDEX CONCURRENTLY
        if sql_upper.startswith('CREATE INDEX CONCURRENTLY'):
            return True
        
        # Allow DROP INDEX CONCURRENTLY
        if sql_upper.startswith('DROP INDEX CONCURRENTLY'):
            return True
        
        # Allow ALTER SYSTEM (for configuration changes)
        if sql_upper.startswith('ALTER SYSTEM'):
            return True
        
        # Allow SET commands (for session configuration)
        if sql_upper.startswith('SET '):
            return True
        
        # Reject all other commands
        logger.warning(f"Unsafe SQL rejected: {sql[:50]}...")
        return False
    
    def _generate_rollback_sql(self, recommendation: Dict[str, Any]) -> str:
        """Generate rollback SQL from recommendation."""
        rollback_sql = recommendation.get('rollback_sql', '')
        if rollback_sql:
            return rollback_sql
        
        # Try to generate rollback from sql_fix
        sql_fix = recommendation.get('sql_fix', '')
        if not sql_fix:
            return ''
        
        sql_upper = sql_fix.upper().strip()
        
        # Handle CREATE INDEX
        if 'CREATE INDEX' in sql_upper:
            # Extract index name and generate DROP INDEX
            match = re.search(r'CREATE INDEX CONCURRENTLY\s+(\w+)', sql_fix, re.IGNORECASE)
            if match:
                index_name = match.group(1)
                return f"DROP INDEX CONCURRENTLY {index_name};"
        
        # Handle SET commands - try to extract original value or use defaults
        if sql_upper.startswith('SET '):
            # Extract parameter name
            match = re.search(r'SET\s+(\w+)\s*=', sql_fix, re.IGNORECASE)
            if match:
                param_name = match.group(1)
                # Provide sensible defaults for common parameters
                defaults = {
                    'work_mem': '4MB',
                    'shared_buffers': '128MB',
                    'effective_cache_size': '4GB',
                    'random_page_cost': '4.0',
                    'seq_page_cost': '1.0'
                }
                default_value = defaults.get(param_name.lower(), 'DEFAULT')
                return f"SET {param_name} = '{default_value}';"
        
        return ''
    
    async def apply_recommendation(self, recommendation_id: str) -> Dict[str, Any]:
        """
        Apply a recommendation by executing DDL changes on the sandbox database.
        
        Args:
            recommendation_id: ID of the recommendation to apply
            
        Returns:
            Dictionary with apply results
        """
        logger.info(f"Applying recommendation: {recommendation_id}")
        
        # Get recommendation details
        recommendation = RecommendationsDB.get_recommendation(recommendation_id)
        if not recommendation:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        if recommendation.get('applied', False):
            raise ValueError(f"Recommendation {recommendation_id} is already applied")
        
        # Get SQL fix
        sql_fix = recommendation.get('sql_fix', '')
        if not sql_fix:
            raise ValueError("No SQL fix found in recommendation")
        
        # Validate SQL safety
        if not self._validate_sql_safety(sql_fix):
            raise ValueError(f"SQL fix is not safe for execution: {sql_fix}")
        
        # Create a unique schema for this apply operation
        schema_name = f"apply_{recommendation_id.replace('-', '_')}_{int(datetime.utcnow().timestamp())}"
        
        conn = None
        try:
            # Get sandbox connection
            conn = await get_sandbox_connection()
            
            # Handle CREATE INDEX CONCURRENTLY (cannot run in transaction)
            sql_upper = sql_fix.strip().upper()
            if 'CREATE INDEX CONCURRENTLY' in sql_upper:
                # CREATE INDEX CONCURRENTLY must run outside transaction
                
                # First, create the schema (can be in transaction)
                async with conn.transaction():
                    await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                    logger.info(f"Created temporary schema: {schema_name}")
                
                # Set search path (outside transaction)
                await conn.execute(f"SET search_path = {schema_name}, public")
                
                # Execute CREATE INDEX CONCURRENTLY (outside transaction)
                await conn.execute(sql_fix)
                logger.info(f"Executed DDL: {sql_fix}")
                
            else:
                # Other DDL can run in transaction
                async with conn.transaction():
                    # Create temporary schema
                    await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                    logger.info(f"Created temporary schema: {schema_name}")
                    
                    # Set search path to include our schema
                    await conn.execute(f"SET search_path = {schema_name}, public")
                    
                    # Execute the DDL change
                    await conn.execute(sql_fix)
                    logger.info(f"Executed DDL: {sql_fix}")
            
            # Store the change record (in separate transaction)
            async with conn.transaction():
                change_record = {
                    'recommendation_id': recommendation_id,
                    'sql_executed': sql_fix,
                    'schema_name': schema_name,
                    'applied_at': datetime.utcnow().isoformat(),
                    'rollback_sql': self._generate_rollback_sql(recommendation),
                    'status': 'applied'
                }
                
                # Store in memory (in production, this would be in a database)
                self._applied_changes[recommendation_id] = change_record
                
                # Update recommendation status
                RecommendationsDB.update_recommendation_status(
                    recommendation_id,
                    'applied',
                    applied=True,
                    applied_at=datetime.utcnow().isoformat()
                )
                
                # Log to audit trail
                await self.audit_logger.log_operation(
                    conn, 'apply', recommendation_id, sql_fix, 'success',
                    {
                        'schema_name': schema_name,
                        'rollback_sql': change_record['rollback_sql'],
                        'recommendation_title': recommendation.get('title', ''),
                        'risk_level': recommendation.get('risk_level', 'unknown'),
                        'original_sql': recommendation.get('sql_fix') or recommendation.get('original_sql') or recommendation.get('query_text') or ''
                    }
                )
                
                logger.info(f"Successfully applied recommendation: {recommendation_id}")
                
                return {
                    'success': True,
                    'recommendation_id': recommendation_id,
                    'sql_executed': sql_fix,
                    'schema_name': schema_name,
                    'applied_at': change_record['applied_at'],
                    'rollback_available': bool(change_record['rollback_sql']),
                    'message': 'Recommendation applied successfully'
                }
            
        except Exception as e:
            logger.error(f"Failed to apply recommendation {recommendation_id}: {e}")
            
            # Log failure to audit trail
            if conn:
                try:
                    await self.audit_logger.log_operation(
                        conn, 'apply', recommendation_id, sql_fix, 'error',
                        {'error_message': str(e)}
                    )
                except Exception:
                    pass  # Don't fail on audit logging errors
            
            raise RuntimeError(f"Failed to apply recommendation: {e}")
        
        finally:
            # Close connection
            if conn:
                try:
                    await conn.close()
                except Exception:
                    pass
    
    async def rollback_recommendation(self, recommendation_id: str) -> Dict[str, Any]:
        """
        Rollback a previously applied recommendation.
        
        Args:
            recommendation_id: ID of the recommendation to rollback
            
        Returns:
            Dictionary with rollback results
        """
        logger.info(f"Rolling back recommendation: {recommendation_id}")
        
        # Check if recommendation was applied
        if recommendation_id not in self._applied_changes:
            raise ValueError(f"Recommendation {recommendation_id} was not applied or change record not found")
        
        change_record = self._applied_changes[recommendation_id]
        
        if change_record.get('status') != 'applied':
            raise ValueError(f"Recommendation {recommendation_id} is not in applied state")
        
        rollback_sql = change_record.get('rollback_sql')
        if not rollback_sql:
            raise ValueError(f"No rollback SQL available for recommendation {recommendation_id}")
        
        conn = None
        try:
            # Get sandbox connection
            conn = await get_sandbox_connection()
            
            # Validate rollback SQL safety
            if not self._validate_sql_safety(rollback_sql):
                raise ValueError(f"Rollback SQL is not safe for execution: {rollback_sql}")
            
            # Set search path to include the schema where changes were applied
            schema_name = change_record.get('schema_name', 'public')
            
            # Handle DROP INDEX CONCURRENTLY (cannot run in transaction)
            rollback_upper = rollback_sql.strip().upper()
            if 'DROP INDEX CONCURRENTLY' in rollback_upper:
                # DROP INDEX CONCURRENTLY must run outside transaction
                
                # Set search path (outside transaction)
                await conn.execute(f"SET search_path = {schema_name}, public")
                
                # Execute DROP INDEX CONCURRENTLY (outside transaction)
                await conn.execute(rollback_sql)
                logger.info(f"Executed rollback: {rollback_sql}")
                
            else:
                # Other DDL can run in transaction
                async with conn.transaction():
                    # Set search path to include the schema where changes were applied
                    await conn.execute(f"SET search_path = {schema_name}, public")
                    
                    await conn.execute(rollback_sql)
                    logger.info(f"Executed rollback: {rollback_sql}")
            
            # Update change record and status (in separate transaction)
            async with conn.transaction():
                # Update change record
                change_record['status'] = 'rolled_back'
                change_record['rolled_back_at'] = datetime.utcnow().isoformat()
                
                # Update recommendation status
                RecommendationsDB.update_recommendation_status(
                    recommendation_id,
                    'active',
                    applied=False,
                    applied_at=None
                )
                
                # Log to audit trail
                await self.audit_logger.log_operation(
                    conn, 'rollback', recommendation_id, rollback_sql, 'success',
                    {
                        'original_apply_schema': schema_name,
                        'original_sql': change_record.get('sql_executed', ''),
                        'applied_at': change_record.get('applied_at', '')
                    }
                )
                
                logger.info(f"Successfully rolled back recommendation: {recommendation_id}")
                
                return {
                    'success': True,
                    'recommendation_id': recommendation_id,
                    'sql_executed': rollback_sql,
                    'rolled_back_at': change_record['rolled_back_at'],
                    'message': 'Recommendation rolled back successfully'
                }
            
        except Exception as e:
            logger.error(f"Failed to rollback recommendation {recommendation_id}: {e}")
            
            # Log failure to audit trail
            if conn:
                try:
                    await self.audit_logger.log_operation(
                        conn, 'rollback', recommendation_id, rollback_sql, 'error',
                        {'error_message': str(e)}
                    )
                except Exception:
                    pass  # Don't fail on audit logging errors
            
            raise RuntimeError(f"Failed to rollback recommendation: {e}")
        
        finally:
            # Close connection
            if conn:
                try:
                    await conn.close()
                except Exception:
                    pass
    
    async def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get the audit trail of all operations."""
        conn = None
        try:
            conn = await get_sandbox_connection()
            
            # Get audit records
            records = await conn.fetch("""
                SELECT operation_type, recommendation_id, sql_executed, status, 
                       timestamp, details, created_at
                FROM optischema_audit_log 
                ORDER BY created_at DESC 
                LIMIT $1
            """, limit)
            
            return [
                {
                    'operation_type': record['operation_type'],
                    'recommendation_id': record['recommendation_id'],
                    'sql_executed': record['sql_executed'],
                    'status': record['status'],
                    'timestamp': record['timestamp'].isoformat(),
                    'details': json.loads(record['details']) if record['details'] else {},
                    'created_at': record['created_at'].isoformat()
                }
                for record in records
            ]
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            return []
        
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception:
                    pass
    
    async def get_applied_changes(self) -> List[Dict[str, Any]]:
        """Get list of all applied changes."""
        return list(self._applied_changes.values())
    
    async def get_change_status(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific change."""
        return self._applied_changes.get(recommendation_id)
    
    async def cleanup_old_schemas(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary schemas created during apply operations.
        
        Args:
            max_age_hours: Maximum age of schemas to keep
            
        Returns:
            Number of schemas cleaned up
        """
        logger.info(f"Cleaning up schemas older than {max_age_hours} hours")
        
        cutoff_time = int(datetime.utcnow().timestamp()) - (max_age_hours * 3600)
        cleaned_count = 0
        
        conn = None
        try:
            # Get sandbox connection
            conn = await get_sandbox_connection()
            
            # Get all schemas starting with 'apply_'
            schemas = await conn.fetch("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'apply_%'
            """)
            
            for schema in schemas:
                schema_name = schema['schema_name']
                
                # Extract timestamp from schema name
                try:
                    if 'apply_' in schema_name:
                        # Format: apply_recommendation_id_timestamp
                        parts = schema_name.split('_')
                        if len(parts) >= 3:
                            timestamp = int(parts[-1])
                            if timestamp < cutoff_time:
                                await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
                                logger.info(f"Dropped old schema: {schema_name}")
                                cleaned_count += 1
                                
                                # Log cleanup to audit trail
                                await self.audit_logger.log_operation(
                                    conn, 'cleanup', 'system', f"DROP SCHEMA {schema_name} CASCADE", 'success',
                                    {'schema_age_hours': (int(datetime.utcnow().timestamp()) - timestamp) / 3600}
                                )
                                
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse timestamp from schema: {schema_name}")
            
        except Exception as e:
            logger.error(f"Error during schema cleanup: {e}")
        
        finally:
            # Close connection
            if conn:
                try:
                    await conn.close()
                except Exception:
                    pass
        
        logger.info(f"Cleaned up {cleaned_count} old schemas")
        return cleaned_count


# Global apply manager instance
apply_manager = ApplyManager()


def get_apply_manager() -> ApplyManager:
    """Get the global apply manager instance."""
    return apply_manager


async def initialize_apply_manager():
    """Initialize the apply manager."""
    logger.info("✅ Initialized apply manager")


async def close_apply_manager():
    """Close the apply manager."""
    logger.info("🛑 Closing apply manager")
    # Clean up old schemas on shutdown
    await apply_manager.cleanup_old_schemas() 