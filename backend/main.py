"""
Main FastAPI application for OptiSchema backend.
Provides health endpoints, CORS configuration.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from connection_manager import connection_manager
from storage import init_db
from models import HealthCheck

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
start_time = time.time()


async def _decommission_snapshot_loop():
    """Background task: take decommission snapshots every 24 hours."""
    import asyncio
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 hours
        try:
            pool = await connection_manager.get_pool()
            if pool:
                from services.schema_health_service import schema_health_service
                result = await schema_health_service.refresh_decommission_snapshots()
                logger.info(f"Auto decommission snapshot: {result}")
        except Exception as e:
            logger.warning(f"Auto decommission snapshot failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting OptiSchema backend...")

    # Initialize SQLite database
    await init_db()

    # Auto-connect if DATABASE_URL is provided (e.g. for Quickstart Demo)
    if settings.database_url:
        logger.info(f"Auto-connecting to database from environment: {settings.database_url}")
        success, error = await connection_manager.connect(settings.database_url)
        if success:
            logger.info("Successfully auto-connected to target database")
        else:
            logger.error(f"Failed to auto-connect to database: {error}")
    else:
        # Target database connection will be established when user provides credentials
        logger.info("Target database connection will be established when user provides credentials")

    # Start background task for decommission snapshots (every 24h)
    import asyncio
    snapshot_task = asyncio.create_task(_decommission_snapshot_loop())

    logger.info("OptiSchema backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down OptiSchema backend...")
    snapshot_task.cancel()

    # Close target database connection pool
    await connection_manager.disconnect()
    logger.info("Target database connection pool closed")

    logger.info("OptiSchema backend shutdown complete")


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

# Import routers
from routers import metrics, analysis, connection, settings as settings_router, health, ai_analysis, cart

# Include routers
app.include_router(metrics.router)
app.include_router(analysis.router)
app.include_router(connection.router, prefix="/api/connection", tags=["connection"])
app.include_router(settings_router.router)
app.include_router(health.router)
app.include_router(ai_analysis.router)
app.include_router(cart.router)


@app.get("/api")
async def api_info():
    """Root API info endpoint."""
    return {
        "message": "OptiSchema API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health/check"
    }


@app.get("/api/health/check", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint for monitoring and docker."""
    try:
        # Check database health
        db_healthy = await connection_manager.check_connection_health()
        
        # Check AI config
        if settings.llm_provider.lower() == "ollama":
            ai_healthy = True
        else:
            ai_healthy = bool(settings.openai_api_key or settings.gemini_api_key or settings.deepseek_api_key)
        
        # Determine overall status
        status = "healthy" if db_healthy else "unhealthy"
        
        return HealthCheck(
            status=status,
            timestamp=datetime.utcnow(),
            database=db_healthy,
            openai=ai_healthy,
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


# Mount static files for the frontend (All-In-One image support)
# IMPORTANT: This must be done AFTER all API routes are defined
from fastapi.staticfiles import StaticFiles
import os

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    # Catch-all route for SPA routing
    # This ensures that refreshing on /dashboard or other routes serves index.html
    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        if not request.url.path.startswith("/api"):
            # Try to serve index.html from the root of the static directory
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                from fastapi.responses import FileResponse
                return FileResponse(index_path)
        return await http_exception_handler(request, exc)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower()
    )
 
