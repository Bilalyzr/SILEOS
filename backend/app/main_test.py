"""
Test FastAPI Application - Testing individual routers
"""

from fastapi import FastAPI, Request, HTTPException
from app.core.cors import setup_cors
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, create_tables

# Import all models to register them with Base
from app.models.user import User
from app.models.course import Course, Lesson
from app.models.quiz import Quiz
from app.models.enrollment import Enrollment
from app.models.payment import Order
from app.models.certificate import Certificate

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    # Initialize database
    await init_db()
    create_tables()

    print("Test Backend Started Successfully!")
    yield

    print("Shutting down Test Backend...")

# Create FastAPI application
app = FastAPI(
    title="SashaInfinity LMS Test API",
    description="SashaInfinity LMS - Test Backend API",
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
        "service": "sashainfinity-lms-test-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SashaInfinity LMS Test Backend API",
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

# Test database connection
@app.get("/api/test-db")
async def test_database():
    """Test database connection and models"""
    try:
        from core.database import get_db
        from models.user import User
        from models.course import Course, Lesson
        from models.quiz import Quiz
        from models.enrollment import Enrollment
        from models.payment import Order
        from models.certificate import Certificate

        # Get database session
        db = next(get_db())

        # Test basic queries
        user_count = db.query(User).count()
        course_count = db.query(Course).count()
        lesson_count = db.query(Lesson).count()
        quiz_count = db.query(Quiz).count()
        enrollment_count = db.query(Enrollment).count()
        order_count = db.query(Order).count()
        certificate_count = db.query(Certificate).count()

        return {
            "database": "connected",
            "models": "loaded successfully",
            "counts": {
                "users": user_count,
                "courses": course_count,
                "lessons": lesson_count,
                "quizzes": quiz_count,
                "enrollments": enrollment_count,
                "orders": order_count,
                "certificates": certificate_count
            }
        }
    except Exception as e:
        return {
            "database": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "main_test:app",
        host="0.0.0.0",
        port=8003,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info"
    )