"""
Email Test FastAPI Application - Testing email service
"""

from fastapi import FastAPI, Request, HTTPException
from app.core.cors import setup_cors
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.utils.email import EmailService, EmailTemplates, send_verification_email

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    print("Email Test Backend Started Successfully!")
    yield
    print("Shutting down Email Test Backend...")

# Create FastAPI application
app = FastAPI(
    title="SashaInfinity LMS Email Test API",
    description="Premium SashaInfinity LMS - Email Test Backend API",
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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sashainfinity-lms-email-test",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SashaInfinity LMS Email Test Backend API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "email_testing": True,
        "status": "running"
    }

# Test email configuration
@app.get("/api/test-email-config")
async def test_email_config():
    """Test email configuration"""
    try:
        email_service = EmailService()

        return {
            "email_config": "loaded",
            "smtp_host": email_service.smtp_host or "not configured",
            "smtp_port": email_service.smtp_port,
            "smtp_user": email_service.smtp_user or "not configured",
            "from_email": email_service.from_email,
            "smtp_configured": bool(email_service.smtp_host and email_service.smtp_user),
            "fallback_mode": not bool(email_service.smtp_host and email_service.smtp_user)
        }
    except Exception as e:
        return {
            "email_config": "error",
            "error": str(e)
        }

# Test email templates
@app.get("/api/test-email-templates")
async def test_email_templates():
    """Test email templates generation"""
    try:
        # Test verification email template
        verification_subject, verification_html, verification_text = EmailTemplates.get_verification_email(
            "John Doe", "https://example.com/verify?token=test123"
        )

        # Test password reset email template
        reset_subject, reset_html, reset_text = EmailTemplates.get_password_reset_email(
            "Jane Smith", "https://example.com/reset?token=reset456"
        )

        # Test enrollment confirmation email template
        enrollment_subject, enrollment_html, enrollment_text = EmailTemplates.get_enrollment_confirmation_email(
            "Student Name", "Python Programming Basics", "https://example.com/course/1"
        )

        return {
            "email_templates": "working",
            "templates": {
                "verification": {
                    "subject": verification_subject,
                    "has_html": len(verification_html) > 0,
                    "has_text": len(verification_text) > 0
                },
                "password_reset": {
                    "subject": reset_subject,
                    "has_html": len(reset_html) > 0,
                    "has_text": len(reset_text) > 0
                },
                "enrollment": {
                    "subject": enrollment_subject,
                    "has_html": len(enrollment_html) > 0,
                    "has_text": len(enrollment_text) > 0
                }
            }
        }
    except Exception as e:
        return {
            "email_templates": "error",
            "error": str(e)
        }

# Test sending email (will use fallback mode if SMTP not configured)
@app.post("/api/test-send-email")
async def test_send_email():
    """Test sending an email (fallback mode if no SMTP)"""
    try:
        email_service = EmailService()

        # Test email content
        test_subject = "Test Email from SashaInfinity LMS Backend"
        test_html = """
        <html>
        <body>
            <h2>Email Test Successful!</h2>
            <p>This is a test email from the SashaInfinity LMS backend system.</p>
            <p>If you're seeing this, the email service is working correctly.</p>
        </body>
        </html>
        """
        test_text = """
        Email Test Successful!

        This is a test email from the SashaInfinity LMS backend system.
        If you're seeing this, the email service is working correctly.
        """

        # Try to send email
        success = await email_service.send_email(
            "test@example.com",
            test_subject,
            test_html,
            test_text
        )

        return {
            "email_sending": "tested",
            "success": success,
            "fallback_mode": not bool(email_service.smtp_host and email_service.smtp_user),
            "message": "Email sent successfully" if success else "Email sending failed"
        }
    except Exception as e:
        return {
            "email_sending": "error",
            "error": str(e)
        }

# Test verification email function
@app.post("/api/test-verification-email")
async def test_verification_email():
    """Test verification email function"""
    try:
        # This will use fallback mode if SMTP not configured
        success = await send_verification_email("test@example.com", "test_token_123")

        return {
            "verification_email": "tested",
            "success": success,
            "test_email": "test@example.com",
            "test_token": "test_token_123",
            "verification_link": f"{settings.FRONTEND_URL}/verify-email?token=test_token_123"
        }
    except Exception as e:
        return {
            "verification_email": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "main_email_test:app",
        host="0.0.0.0",
        port=8005,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info"
    )