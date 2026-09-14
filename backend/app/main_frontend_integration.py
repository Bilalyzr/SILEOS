"""
Frontend Integration Test Server - Matches frontend API expectations
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from app.core.cors import setup_cors
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, create_tables, get_db

# Import all models to ensure they're registered
from app.models.user import User
from app.models.course import Course, Lesson
from app.models.quiz import Quiz
from app.models.enrollment import Enrollment
from app.models.payment import Order
from app.models.certificate import Certificate

# Import routers
from app.routers import auth, courses, users, certificates, payments, admin

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    await init_db()
    create_tables()
    print("Frontend Integration Test Backend Started on port 8000!")
    yield
    print("Shutting down Frontend Integration Test Backend...")

# Create FastAPI application
app = FastAPI(
    title="SashaInfinity LMS Frontend Integration API",
    description="Premium SashaInfinity LMS - Frontend Integration Test",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# CORS Middleware (centralized)
setup_cors(app)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(certificates.router, prefix="/api/v1/certificates", tags=["Certificates"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sashainfinity-lms-frontend-integration",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "frontend_ready": True
    }

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SashaInfinity LMS Frontend Integration API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "frontend_integration": True,
        "status": "running",
        "api_prefix": "/api/v1"
    }

# API v1 Routes (matching frontend expectations)
@app.get("/api/v1/health")
async def api_health():
    """API health check"""
    return {
        "status": "ok",
        "message": "SashaInfinity LMS API is running",
        "version": "1.0.0"
    }

# Payment endpoints
@app.post("/api/v1/payments/create-order")
async def create_payment_order():
    """Create payment order"""
    return {
        "order_id": "order_test_123456",
        "amount": 99900,  # in paise
        "currency": "INR",
        "status": "created",
        "razorpay_order_id": "order_test_123456"
    }

@app.post("/api/v1/payments/verify")
async def verify_payment():
    """Verify payment"""
    return {
        "success": True,
        "message": "Payment verified successfully",
        "enrollment_created": True
    }

# Test database connectivity
@app.get("/api/v1/test/database")
async def test_database_connection(db: Session = Depends(get_db)):
    """Test database connectivity"""
    try:
        # Test queries on all main tables
        user_count = db.query(User).count()
        course_count = db.query(Course).count()
        lesson_count = db.query(Lesson).count()
        quiz_count = db.query(Quiz).count()
        enrollment_count = db.query(Enrollment).count()
        order_count = db.query(Order).count()
        certificate_count = db.query(Certificate).count()

        return {
            "database": "connected",
            "models": "working",
            "counts": {
                "users": user_count,
                "courses": course_count,
                "lessons": lesson_count,
                "quizzes": quiz_count,
                "enrollments": enrollment_count,
                "orders": order_count,
                "certificates": certificate_count
            },
            "message": "Database fully operational"
        }
    except Exception as e:
        return {
            "database": "error",
            "error": str(e),
            "message": "Database connection failed"
        }

# Test frontend connectivity
@app.get("/api/v1/test/frontend")
async def test_frontend_connectivity(request: Request):
    """Test frontend-backend connectivity"""
    return {
        "backend": "reachable",
        "cors": "enabled",
        "client_ip": request.client.host,
        "headers": dict(request.headers),
        "api_version": "v1",
        "message": "Frontend can successfully reach backend"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main_frontend_integration:app",
        host="0.0.0.0",
        port=8000,  # Frontend expects this port
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info"
    )