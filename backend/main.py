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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting OptiSchema backend...")
    
    # Initialize SQLite database
    await init_db()
    
    # Target database connection will be established when user provides credentials
    logger.info("✅ Target database connection will be established when user provides credentials")
    
    logger.info("✅ OptiSchema backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down OptiSchema backend...")
    
    # Close target database connection pool
    await connection_manager.disconnect()
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

# Import routers
from routers import metrics, analysis, connection, settings as settings_router, health, ai_analysis

# Include routers
app.include_router(metrics.router)
app.include_router(analysis.router)
app.include_router(connection.router, prefix="/api/connection", tags=["connection"])
app.include_router(settings_router.router)
app.include_router(health.router)
app.include_router(ai_analysis.router)


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
        db_healthy = await connection_manager.check_connection_health()
        
        # Check OpenAI API (basic check - we'll implement this later)
        openai_healthy = bool(settings.openai_api_key)
        
        # Determine overall status
        status = "healthy" if db_healthy else "unhealthy"
        
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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower()
    )
 