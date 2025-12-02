"""
Main FastAPI application for OptiSchema backend.
Provides health endpoints, CORS configuration, and WebSocket support.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import APIRouter

from config import settings
from db import initialize_database, close_pool, health_check as db_health_check
from models import HealthCheck, WebSocketMessage, APIResponse
from collector import poll_pg_stat, get_metrics_cache, initialize_collector
from analysis.pipeline import start_analysis_scheduler
from tenant_context import tenant_middleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting OptiSchema backend...")
    
    # Initialize OptiSchema metadata database (for storing recommendations, analysis, etc.)
    from metadata_db import initialize_metadata_db
    metadata_db_ready = await initialize_metadata_db()
    if metadata_db_ready:
        logger.info("✅ OptiSchema metadata database initialized")
    else:
        logger.warning("⚠️  Metadata database not ready - recommendations storage may not work")
    
    # Target database connection will be established when user provides credentials
    logger.info("✅ Target database connection will be established when user provides credentials")
    
    # Initialize the collector with connection change callback
    initialize_collector()
    
    # Collector task will be started when user connects to database
    collector_task = None
    logger.info("✅ Collector ready - will start when database connection is established")
    
    # Start the analysis scheduler
    loop = asyncio.get_event_loop()
    analysis_task = loop.create_task(start_analysis_scheduler())
    logger.info("✅ Started analysis scheduler")
    
    # Start the job manager
    from job_manager import start_job_manager
    await start_job_manager()
    logger.info("✅ Started job manager")
    
    # Initialize replica manager
    from replica_manager import initialize_replica_manager
    await initialize_replica_manager()
    logger.info("✅ Initialized replica manager")
    
    # Initialize apply manager
    from apply_manager import initialize_apply_manager
    await initialize_apply_manager()
    logger.info("✅ Initialized apply manager")
    
    logger.info("✅ OptiSchema backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down OptiSchema backend...")
    
    # Cancel the collector task
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Collector task cancelled")
    
    # Cancel the analysis task
    analysis_task.cancel()
    try:
        await analysis_task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Analysis task cancelled")
    
    # Stop the job manager
    from job_manager import stop_job_manager
    await stop_job_manager()
    logger.info("✅ Job manager stopped")
    
    # Close replica manager
    from replica_manager import close_replica_manager
    await close_replica_manager()
    logger.info("✅ Replica manager closed")
    
    # Close apply manager
    from apply_manager import close_apply_manager
    await close_apply_manager()
    logger.info("✅ Apply manager closed")
    
    # Close metadata database connection pool
    from metadata_db import close_metadata_db
    await close_metadata_db()
    logger.info("✅ Metadata database connection closed")
    
    # Close target database connection pool
    await close_pool()
    logger.info("✅ Target database connection pool closed")
    
    logger.info("✅ OptiSchema backend shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="OptiSchema API",
    description="AI-assisted PostgreSQL performance optimization service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tenant middleware
app.middleware("http")(tenant_middleware)




# Import routers
from routers import metrics_router, suggestions_router, analysis_router
from routers import connection, audit, connection_baseline, index_advisor
from routers import benchmark, apply

# Include routers
app.include_router(metrics_router)
app.include_router(suggestions_router)
app.include_router(analysis_router)
app.include_router(benchmark.router, prefix="/api", tags=["benchmark"])
app.include_router(connection.router, prefix="/api/connection", tags=["connection"])
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(connection_baseline.router, prefix="/api", tags=["connection-baseline"])
app.include_router(index_advisor.router, prefix="/api", tags=["index-advisor"])
app.include_router(apply.router, tags=["apply"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "OptiSchema API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database health
        db_healthy = await db_health_check()
        
        # Check OpenAI API (basic check - we'll implement this later)
        openai_healthy = bool(settings.openai_api_key)
        
        # Determine overall status
        status = "healthy" if db_healthy and openai_healthy else "unhealthy"
        
        return HealthCheck(
            status=status,
            timestamp=datetime.utcnow(),
            database=db_healthy,
            openai=openai_healthy,
            version="1.0.0",
            uptime=time.time() - start_time
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database=False,
            openai=False,
            version="1.0.0",
            uptime=time.time() - start_time
        )


@app.get("/api/health")
async def api_health():
    """API health check endpoint."""
    return await health_check()


# Import WebSocket module
from websocket import handle_websocket_connection

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await handle_websocket_connection(websocket)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error": str(exc)
        }
    )


# Import and include routers (we'll create these in the next steps)
# from routers import metrics, suggestions, analysis, connection
# app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
# app.include_router(suggestions.router, prefix="/api/suggestions", tags=["suggestions"])
# app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower()
    ) 