"""
Connection Router for OptiSchema Slim.
Handles database connection management.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from connection_manager import connection_manager
from storage import (
    save_connection,
    get_saved_connections,
    get_connection_with_password,
    delete_saved_connection,
    update_last_used,
    DuplicateConnectionError
)

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionRequest(BaseModel):
    connection_string: str

class ConnectionResponse(BaseModel):
    success: bool
    message: str

class SaveConnectionRequest(BaseModel):
    name: str
    host: str
    port: str
    database: str
    username: str
    password: str
    ssl: bool = False

@router.post("/connect", response_model=ConnectionResponse)
async def connect_database(request: ConnectionRequest):
    """
    Connect to a database using a connection string.
    """
    success, error_message = await connection_manager.connect(request.connection_string)
    if success:
        return ConnectionResponse(success=True, message="Connected successfully")
    else:
        detail = error_message or "Failed to connect to database"
        raise HTTPException(status_code=400, detail=detail)

@router.post("/disconnect", response_model=ConnectionResponse)
async def disconnect_database():
    """
    Disconnect from the current database.
    """
    await connection_manager.disconnect()
    return ConnectionResponse(success=True, message="Disconnected successfully")

@router.get("/status")
async def get_status():
    """
    Get current connection status with connection details.
    """
    is_healthy = await connection_manager.check_connection_health()
    config = connection_manager.get_connection_config()
    
    # Check if current connection matches a saved connection
    saved_connection_id = None
    if config:
        saved_connections = await get_saved_connections()
        for saved in saved_connections:
            if (saved["host"] == config.get("host") and
                saved["port"] == config.get("port") and
                saved["database"] == config.get("database") and
                saved["username"] == config.get("username")):
                saved_connection_id = saved["id"]
                break
    
    return {
        "connected": is_healthy,
        "current_config": config if is_healthy else None,
        "saved_connection_id": saved_connection_id,
        "connection_history": []  # For future implementation
    }

@router.get("/saved")
async def list_saved_connections():
    """
    List all saved connections (without passwords).
    """
    connections = await get_saved_connections()
    return {"connections": connections}

@router.post("/save")
async def save_current_connection(request: SaveConnectionRequest):
    """
    Save a connection with a name. Can be current connection or a new one.
    If password is empty and we have a current connection, extract from connection string.
    """
    password = request.password
    
    # If password not provided, try to extract from current connection string
    if not password:
        config = connection_manager.get_connection_config()
        if config:
            # Try connection_string first
            if config.get("connection_string"):
                from urllib.parse import urlparse, unquote
                try:
                    parsed = urlparse(config["connection_string"])
                    if parsed.password:
                        password = unquote(parsed.password)
                except Exception as e:
                    logger.warning(f"Could not parse connection string: {e}")
            
            # Also try to get from storage (active_connection setting)
            if not password:
                from storage import get_setting
                connection_string = await get_setting('active_connection')
                if connection_string:
                    from urllib.parse import urlparse, unquote
                    try:
                        parsed = urlparse(connection_string)
                        if parsed.password:
                            password = unquote(parsed.password)
                    except Exception as e:
                        logger.warning(f"Could not parse stored connection string: {e}")
    
    if not password:
        raise HTTPException(
            status_code=400, 
            detail="Password is required to save connection. Please provide the password or ensure you're connected to the database."
        )
    
    try:
        connection_id = await save_connection(
            name=request.name,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=password,
            ssl=request.ssl
        )
        return {
            "success": True,
            "message": f"Connection '{request.name}' saved successfully",
            "connection_id": connection_id
        }
    except DuplicateConnectionError as e:
        # Same credentials already exist under a different name
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_credentials",
                "message": f"This database connection already exists as '{e.existing_name}'.",
                "existing_name": e.existing_name,
                "existing_id": e.existing_id
            }
        )
    except Exception as e:
        error_msg = str(e)
        # Check if it's a unique constraint violation (duplicate name)
        if "UNIQUE constraint failed" in error_msg:
            if "saved_connections.name" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "duplicate_name",
                        "message": f"A connection with the name '{request.name}' already exists. Please use a different name."
                    }
                )
            # Handle unique index on credentials (fallback)
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "duplicate_credentials",
                    "message": "A connection with these credentials already exists."
                }
            )
        raise HTTPException(status_code=400, detail=f"Failed to save connection: {error_msg}")

@router.post("/switch/{connection_id}")
async def switch_to_saved_connection(connection_id: int):
    """
    Switch to a saved connection by ID.
    """
    connection = await get_connection_with_password(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Build connection string
    from urllib.parse import quote_plus
    user = quote_plus(connection["username"])
    password = quote_plus(connection["password"])
    db = quote_plus(connection["database"])
    
    # Auto-detect RDS hosts and require SSL
    is_rds_host = ".rds.amazonaws.com" in connection["host"] or ".rds.amazonaws.com.cn" in connection["host"]
    needs_ssl = connection.get("ssl", False) or is_rds_host
    
    conn_string = f"postgresql://{user}:{password}@{connection['host']}:{connection['port']}/{db}"
    if needs_ssl:
        conn_string += "?sslmode=require"
    
    # Connect using the connection string
    success, error_message = await connection_manager.connect(conn_string)
    if success:
        await update_last_used(connection_id)
        return {
            "success": True,
            "message": f"Switched to connection '{connection['name']}'"
        }
    else:
        raise HTTPException(status_code=400, detail=error_message or "Failed to connect")

@router.delete("/saved/{connection_id}")
async def delete_saved_connection_endpoint(connection_id: int):
    """
    Delete a saved connection.
    """
    try:
        await delete_saved_connection(connection_id)
        return {"success": True, "message": "Connection deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete connection: {str(e)}")

@router.get("/extension/status")
async def get_extensions_status():
    """
    Get status of all relevant Postgres extensions.
    """
    from services.extension_service import extension_service
    status = await extension_service.get_extensions_status()
    return {"extensions": status}

@router.post("/extension/enable/{name}")
async def enable_extension(name: str):
    """
    Enable a specific extension.
    """
    from services.extension_service import extension_service
    result = await extension_service.enable_extension(name)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@router.get("/extension/check")
async def legacy_check_extension():
    """Legacy endpoint for backward compatibility."""
    from services.extension_service import extension_service
    status = await extension_service.get_extensions_status()
    enabled = any(e['name'] == 'pg_stat_statements' and e['enabled'] for e in status)
    return {"enabled": enabled}

@router.post("/extension/enable")
async def legacy_enable_extension():
    """Legacy endpoint for backward compatibility."""
    from services.extension_service import extension_service
    result = await extension_service.enable_extension("pg_stat_statements")
    if result["success"]:
        return {"success": True, "message": "Extension enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@router.get("/extension/hypopg/check")
async def legacy_check_hypopg():
    """Legacy endpoint for backward compatibility."""
    from services.extension_service import extension_service
    status = await extension_service.get_extensions_status()
    enabled = any(e['name'] == 'hypopg' and e['enabled'] for e in status)
    return {"enabled": enabled, "extension": "hypopg"}

@router.post("/extension/hypopg/enable")
async def legacy_enable_hypopg():
    """Legacy endpoint for backward compatibility."""
    from services.extension_service import extension_service
    result = await extension_service.enable_extension("hypopg")
    if result["success"]:
        return {"success": True, "message": "HypoPG extension enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail=result["message"])