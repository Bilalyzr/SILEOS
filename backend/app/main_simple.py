"""
Simplified SashaInfinity LMS Backend - FastAPI Application
Test version with minimal dependencies
"""

from fastapi import FastAPI, Request, HTTPException
from app.core.cors import setup_cors
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, create_tables

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    # Initialize database
    await init_db()
    create_tables()

    print("SashaInfinity LMS Backend Started Successfully!")
    yield

    print("Shutting down SashaInfinity LMS Backend...")

# Create FastAPI application
app = FastAPI(
    title="SashaInfinity LMS API",
    description="Premium SashaInfinity LMS - Backend API",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# CORS Middleware (centralized)
setup_cors(app)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker containers"""
    return {
        "status": "healthy",
        "service": "sashainfinity-lms-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SashaInfinity LMS Backend API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "premium_lms": True,
        "status": "running"
    }

# Exception Handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Basic API endpoints for testing

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "API is working!",
        "database": "connected",
        "authentication": "ready",
        "features": [
            "User Management",
            "Course Management",
            "Payment Processing",
            "Certificate Generation",
            "Admin Panel"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info"
    )