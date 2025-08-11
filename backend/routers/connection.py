from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncpg
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from connection_manager import connection_manager
from db import get_pool

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionTestRequest(BaseModel):
    host: Optional[str] = None
    port: Optional[str] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: Optional[bool] = False
    connection_string: Optional[str] = None

class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None

class ConnectionStatusResponse(BaseModel):
    connected: bool
    current_config: Optional[Dict[str, Any]] = None
    connection_history: list = []

class ConnectionSwitchRequest(BaseModel):
    host: str
    port: str
    database: str
    username: str
    password: str
    ssl: Optional[bool] = False

@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(request: ConnectionTestRequest):
    """Test database connection and check for pg_stat_statements extension."""
    
    # Parse connection string or build from components
    if request.connection_string:
        # For connection string, we need to parse it to get config
        try:
            # Simple parsing - in production, use proper URL parsing
            url = request.connection_string
            if url.startswith("postgresql://"):
                parts = url.replace("postgresql://", "").split("@")
                if len(parts) == 2:
                    auth, rest = parts
                    user_pass = auth.split(":")
                    host_port_db = rest.split("/")
                    if len(host_port_db) == 2:
                        host_port, db = host_port_db
                        host_port_parts = host_port.split(":")
                        host = host_port_parts[0]
                        port = int(host_port_parts[1]) if len(host_port_parts) > 1 else 5432
                        user = user_pass[0]
                        password = user_pass[1] if len(user_pass) > 1 else ""
                        
                        config = {
                            "host": host,
                            "port": port,
                            "database": db,
                            "user": user,
                            "password": password
                        }
                    else:
                        raise ValueError("Invalid connection string format")
                else:
                    raise ValueError("Invalid connection string format")
            else:
                raise ValueError("Invalid connection string format")
        except Exception as e:
            return ConnectionTestResponse(
                success=False,
                message=f"Invalid connection string: {str(e)}"
            )
    else:
        # Build config from individual components
        config = {
            "host": request.host or "localhost",
            "port": int(request.port) if request.port else 5432,
            "database": request.database or "postgres",
            "user": request.username or "postgres",
            "password": request.password or ""
        }
    
    # Test the connection using the connection manager
    result = await connection_manager.test_connection(config)
    return ConnectionTestResponse(**result)

@router.post("/switch", response_model=ConnectionTestResponse)
async def switch_database(request: ConnectionSwitchRequest):
    """Switch to a new database connection."""
    
    config = {
        "host": request.host,
        "port": int(request.port),
        "database": request.database,
        "user": request.username,
        "password": request.password,
        "ssl": request.ssl
    }
    
    # Test the connection first
    test_result = await connection_manager.test_connection(config)
    if not test_result['success']:
        return ConnectionTestResponse(**test_result)
    
    # Switch to the new connection
    success = await connection_manager.connect(config)
    
    if success:
        return ConnectionTestResponse(
            success=True,
            message=f"Successfully connected to {config['host']}:{config['port']}/{config['database']}",
            details=test_result['details']
        )
    else:
        return ConnectionTestResponse(
            success=False,
            message="Failed to establish connection"
        )

@router.get("/status", response_model=ConnectionStatusResponse)
async def get_connection_status():
    """Get current connection status and history."""
    
    # Check if we have a connection and if it's actually healthy
    is_healthy = await connection_manager.check_connection_health()
    current_config = connection_manager.get_current_config() if is_healthy else None
    history = connection_manager.get_connection_history()
    
    # If not connected, return empty history to keep things clean
    if not is_healthy:
        return ConnectionStatusResponse(
            connected=False,
            current_config=None,
            connection_history=[]
        )
    
    return ConnectionStatusResponse(
        connected=True,
        current_config=current_config,
        connection_history=history
    )

@router.post("/disconnect")
async def disconnect_database():
    """Disconnect from the current database."""
    
    await connection_manager.disconnect()
    
    return {
        "success": True,
        "message": "Disconnected from database"
    }


@router.get("/ping")
async def ping_current_database() -> Dict[str, Any]:
    """Measure a lightweight round-trip to the current database using SELECT 1."""
    try:
        pool = await get_pool()
        if not pool:
            return {"success": False, "error": "No active database connection"}
        start = asyncio.get_event_loop().time()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        end = asyncio.get_event_loop().time()
        duration_ms = (end - start) * 1000.0
        return {"success": True, "duration_ms": round(duration_ms, 2), "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/sandbox-ping")
async def ping_sandbox_database() -> Dict[str, Any]:
    """Measure a lightweight round-trip to the sandbox database using SELECT 1."""
    try:
        from sandbox import get_sandbox_connection
        conn = await get_sandbox_connection()
        start = asyncio.get_event_loop().time()
        await conn.fetchval("SELECT 1")
        end = asyncio.get_event_loop().time()
        try:
            await conn.close()
        except Exception:
            pass
        duration_ms = (end - start) * 1000.0
        return {"success": True, "duration_ms": round(duration_ms, 2), "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Sandbox ping failed: {e}")
        return {"success": False, "error": str(e)}

@router.post("/clear-history")
async def clear_connection_history():
    """Clear the connection history."""
    
    connection_manager.clear_connection_history()
    
    return {
        "success": True,
        "message": "Connection history cleared"
    }

@router.post("/connect")
async def connect_database(request: ConnectionTestRequest):
    """Establish a persistent connection to the database."""
    # This endpoint is now deprecated in favor of /switch
    # For backward compatibility, we'll redirect to /switch
    
    if not request.connection_string and not all([request.host, request.database, request.username]):
        raise HTTPException(
            status_code=400,
            detail="Either connection_string or host, database, and username are required"
        )
    
    # Convert to switch request format
    if request.connection_string:
        # Parse connection string
        url = request.connection_string
        if url.startswith("postgresql://"):
            parts = url.replace("postgresql://", "").split("@")
            if len(parts) == 2:
                auth, rest = parts
                user_pass = auth.split(":")
                host_port_db = rest.split("/")
                if len(host_port_db) == 2:
                    host_port, db = host_port_db
                    host_port_parts = host_port.split(":")
                    host = host_port_parts[0]
                    port = host_port_parts[1] if len(host_port_parts) > 1 else "5432"
                    user = user_pass[0]
                    password = user_pass[1] if len(user_pass) > 1 else ""
                    
                    switch_request = ConnectionSwitchRequest(
                        host=host,
                        port=port,
                        database=db,
                        username=user,
                        password=password,
                        ssl=request.ssl
                    )
                else:
                    raise HTTPException(status_code=400, detail="Invalid connection string")
            else:
                raise HTTPException(status_code=400, detail="Invalid connection string")
        else:
            raise HTTPException(status_code=400, detail="Invalid connection string")
    else:
        switch_request = ConnectionSwitchRequest(
            host=request.host or "localhost",
            port=request.port or "5432",
            database=request.database or "postgres",
            username=request.username or "postgres",
            password=request.password or "",
            ssl=request.ssl
        )
    
    # Use the switch endpoint
    return await switch_database(switch_request) 

@router.post("/enable-pg-stat")
async def enable_pg_stat_statements() -> Dict[str, Any]:
    """Enable pg_stat_statements extension if not already enabled."""
    try:
        config = connection_manager.get_current_config()
        if not config:
            raise HTTPException(status_code=400, detail="No active database connection")
        
        result = await connection_manager.enable_pg_stat_statements(config)
        return result
    except Exception as e:
        logger.error(f"Error enabling pg_stat_statements: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable pg_stat_statements: {str(e)}")


@router.get("/pg-stat-info")
async def get_pg_stat_statements_info() -> Dict[str, Any]:
    """Get pg_stat_statements status and statistics."""
    try:
        # Inline the pg_stat_statements info logic to avoid circular imports
        pool = await get_pool()
        if not pool:
            return {"available": False, "error": "No database connection"}
        
        async with pool.acquire() as conn:
            # Check if pg_stat_statements exists
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_available_extensions 
                    WHERE name = 'pg_stat_statements'
                )
            """)
            
            if not exists:
                return {"available": False, "error": "pg_stat_statements extension not available"}
            
            # Check if it's enabled
            enabled = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension 
                    WHERE extname = 'pg_stat_statements'
                )
            """)
            
            if not enabled:
                return {"available": True, "enabled": False, "error": "pg_stat_statements not enabled"}
            
            # Get statistics
            total_queries = await conn.fetchval("""
                SELECT COUNT(*) as total_queries 
                FROM pg_stat_statements
                WHERE query NOT ILIKE 'EXPLAIN%' AND query NOT ILIKE 'DEALLOCATE%'
            """)
            
            # Get configuration
            max_config = await conn.fetchval(
                "SELECT setting FROM pg_settings WHERE name = 'pg_stat_statements.max'"
            )
            
            SAMPLING_THRESHOLD = 100000
            
            return {
                "available": True,
                "enabled": True,
                "total_queries": total_queries,
                "max_statements": int(max_config) if max_config else None,
                "large_dataset": total_queries > SAMPLING_THRESHOLD,
                "memory_warning": total_queries > 200000
            }
            
    except Exception as e:
        logger.error(f"Error getting pg_stat_statements info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pg_stat_statements info: {str(e)}")


@router.post("/reset-pg-stat")
async def reset_pg_stat_statements() -> Dict[str, Any]:
    """Reset pg_stat_statements data (clears all collected statistics)."""
    try:
        pool = await get_pool()
        if not pool:
            raise HTTPException(status_code=500, detail="No database connection available")
        
        async with pool.acquire() as conn:
            # Check if user has permissions
            await conn.execute("SELECT pg_stat_statements_reset()")
            
        logger.info("pg_stat_statements reset successfully")
        return {
            "success": True,
            "message": "pg_stat_statements data has been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting pg_stat_statements: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset pg_stat_statements: {str(e)}") 