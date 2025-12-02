"""
Tenant context management for OptiSchema backend.
Handles tenant resolution, validation, and context propagation.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from contextvars import ContextVar
import asyncpg

from config import settings

logger = logging.getLogger(__name__)

# Context variable for storing current tenant_id
tenant_context: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)

# Default tenant ID for backward compatibility
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

class TenantContext:
    """Manages tenant context throughout the application."""
    
    @staticmethod
    def set_tenant_id(tenant_id: str) -> None:
        """Set the current tenant ID in context."""
        tenant_context.set(tenant_id)
        logger.debug(f"Set tenant context to: {tenant_id}")
    
    @staticmethod
    def get_tenant_id() -> Optional[str]:
        """Get the current tenant ID from context."""
        return tenant_context.get()
    
    @staticmethod
    def get_tenant_id_or_default() -> str:
        """Get the current tenant ID or return default if none set."""
        tenant_id = tenant_context.get()
        return tenant_id if tenant_id else DEFAULT_TENANT_ID
    
    @staticmethod
    def clear_tenant_id() -> None:
        """Clear the current tenant ID from context."""
        tenant_context.set(None)
        logger.debug("Cleared tenant context")

async def resolve_tenant_id(request: Request) -> str:
    """
    Resolve tenant ID from request headers or return default.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Resolved tenant ID
        
    Raises:
        HTTPException: If tenant ID is invalid
    """
    # Try to get tenant ID from X-Tenant-ID header
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        # Fall back to default tenant for backward compatibility
        tenant_id = DEFAULT_TENANT_ID
        logger.debug(f"No X-Tenant-ID header found, using default tenant: {tenant_id}")
    else:
        # Validate tenant ID format
        try:
            uuid.UUID(tenant_id)
        except ValueError:
            logger.warning(f"Invalid tenant ID format: {tenant_id}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid tenant ID format: {tenant_id}"
            )
        
        # Only validate non-default tenants (and only if we have a DB connection)
        # This allows the app to work before OptiSchema metadata DB is connected
        if tenant_id != DEFAULT_TENANT_ID:
            if not await validate_tenant_exists(tenant_id):
                logger.warning(f"Tenant not found: {tenant_id}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Tenant not found: {tenant_id}"
                )
    
    # Set in context for this request
    TenantContext.set_tenant_id(tenant_id)
    return tenant_id

async def validate_tenant_exists(tenant_id: str) -> bool:
    """
    Validate that a tenant exists in the database.
    
    Args:
        tenant_id: Tenant ID to validate
        
    Returns:
        bool: True if tenant exists, False otherwise
    """
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.error("No database connection available for tenant validation")
            return False
        
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM optischema.tenants WHERE id = $1 AND status = 'active')",
                tenant_id
            )
            return bool(result)
            
    except Exception as e:
        logger.error(f"Error validating tenant {tenant_id}: {e}")
        return False

async def get_tenant_connection_config(tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    Get connection configuration for a specific tenant.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Dict with connection config or None if not found
    """
    try:
        from connection_manager import connection_manager
        
        pool = await connection_manager.get_pool()
        if not pool:
            logger.error("No database connection available for tenant config lookup")
            return None
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT host, port, database_name, username, password, name
                FROM optischema.tenant_connections 
                WHERE tenant_id = $1 AND name = 'default'
                """,
                tenant_id
            )
            
            if result:
                return {
                    'host': result['host'],
                    'port': result['port'],
                    'database': result['database_name'],
                    'user': result['username'],
                    'password': result['password'],
                    'name': result['name']
                }
            return None
            
    except Exception as e:
        logger.error(f"Error getting tenant connection config for {tenant_id}: {e}")
        return None

def require_tenant_context(func):
    """
    Decorator to ensure tenant context is set before executing a function.
    
    Usage:
        @require_tenant_context
        async def some_function():
            tenant_id = TenantContext.get_tenant_id()
            # ... function logic
    """
    async def wrapper(*args, **kwargs):
        tenant_id = TenantContext.get_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Tenant context not set. Ensure X-Tenant-ID header is provided."
            )
        return await func(*args, **kwargs)
    return wrapper

def get_tenant_filter_clause() -> str:
    """
    Get SQL WHERE clause for filtering by current tenant.
    
    Returns:
        str: SQL WHERE clause with tenant_id filter
    """
    tenant_id = TenantContext.get_tenant_id_or_default()
    return f"tenant_id = '{tenant_id}'"

def add_tenant_to_insert_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add tenant_id to data dictionary for database inserts.
    
    Args:
        data: Data dictionary to add tenant_id to
        
    Returns:
        Dict with tenant_id added
    """
    tenant_id = TenantContext.get_tenant_id_or_default()
    data['tenant_id'] = tenant_id
    return data

def add_tenant_to_where_clause(where_clause: str = "") -> str:
    """
    Add tenant_id filter to existing WHERE clause.
    
    Args:
        where_clause: Existing WHERE clause (optional)
        
    Returns:
        str: WHERE clause with tenant_id filter added
    """
    tenant_id = TenantContext.get_tenant_id_or_default()
    tenant_filter = f"tenant_id = '{tenant_id}'"
    
    if where_clause:
        return f"({where_clause}) AND {tenant_filter}"
    else:
        return tenant_filter

# Middleware for automatic tenant resolution
async def tenant_middleware(request: Request, call_next):
    """
    Middleware to automatically resolve and set tenant context.
    """
    try:
        # Resolve tenant ID from request
        tenant_id = await resolve_tenant_id(request)
        
        # Process request
        response = await call_next(request)
        
        return response
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like invalid tenant)
        raise e
    except Exception as e:
        logger.error(f"Error in tenant middleware: {e}")
        # Clear tenant context on error
        TenantContext.clear_tenant_id()
        raise HTTPException(
            status_code=500,
            detail="Internal server error in tenant resolution"
        )
    finally:
        # Clear tenant context after request
        TenantContext.clear_tenant_id()