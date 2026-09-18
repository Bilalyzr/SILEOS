"""
Enhanced Security Configuration for SashaInfinity LMS
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
import secrets

class Settings(BaseSettings):
    """Enhanced security-aware application settings"""

    # Environment
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    # Production APIs never own recurring jobs; deploy the runtime worker.
    BACKGROUND_TASK_MODE: str = Field(default="worker", pattern="^(worker|inline|disabled)$")
    RUNTIME_METRICS_ENABLED: bool = Field(default=True)
    SENTRY_DSN: str = Field(default="")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.05, ge=0, le=1)
    OBSERVABILITY_TOKEN: str = Field(default="")
    # Dev convenience: when True, new registrations are marked email-verified
    # immediately so they can log in without the email step. Keep False in prod.
    AUTO_VERIFY_EMAIL: bool = Field(default=False, env="AUTO_VERIFY_EMAIL")

    # Firebase Admin SDK — used to mirror email/password registrations into
    # Firebase Authentication. FIREBASE_CREDENTIALS_PATH points at the
    # service-account JSON (falls back to GOOGLE_APPLICATION_CREDENTIALS /
    # Application Default Credentials). If unset/missing, user sync is a no-op.
    FIREBASE_PROJECT_ID: str = Field(default="sashainfinity-720cb", env="FIREBASE_PROJECT_ID")
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(default=None, env="FIREBASE_CREDENTIALS_PATH")

    # Generate secure secrets if not provided
    @validator('SECRET_KEY', pre=True)
    def generate_secret_key(cls, v):
        if v == "your-secret-key-change-in-production-min-32-chars" or not v:
            return secrets.token_urlsafe(64)
        return v

    @validator('JWT_SECRET', pre=True)
    def generate_jwt_secret(cls, v):
        if v == "your-jwt-secret-change-in-production" or not v:
            return secrets.token_urlsafe(64)
        return v

    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL")

    # Redis
    REDIS_URL: str = Field(env="REDIS_URL")

    # Enhanced Security Settings
    SECRET_KEY: str = Field(env="SECRET_KEY")
    JWT_SECRET: str = Field(env="JWT_SECRET")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # Shorter for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=3, env="REFRESH_TOKEN_EXPIRE_DAYS")  # Shorter for security

    # Password Security
    MIN_PASSWORD_LENGTH: int = Field(default=12, env="MIN_PASSWORD_LENGTH")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    LOCKOUT_DURATION_MINUTES: int = Field(default=15, env="LOCKOUT_DURATION_MINUTES")
    PASSWORD_CHANGE_FREQUENCY_DAYS: int = Field(default=90, env="PASSWORD_CHANGE_FREQUENCY_DAYS")

    # Session Security
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    MAX_CONCURRENT_SESSIONS: int = Field(default=3, env="MAX_CONCURRENT_SESSIONS")

    # Storage paths (overridable per env / deploy target)
    # Keep the code portable outside Docker. Container deployments pin this
    # explicitly to /app/uploads in Compose, while local development and tests
    # resolve the default beneath the repository instead of trying to write to
    # the host's filesystem root ("C:\\app" on Windows).
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")

    # Rate Limiting
    # Sized for the SPA: one dashboard load fires ~9 API calls and the app
    # runs background pollers, so 60/min locked out active learners. Buckets
    # are per authenticated user (per IP when anonymous) over fixed windows.
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=200, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_REQUESTS_PER_HOUR: int = Field(default=4000, env="RATE_LIMIT_REQUESTS_PER_HOUR")
    RATE_LIMIT_LOGIN_ATTEMPTS: int = Field(default=5, env="RATE_LIMIT_LOGIN_ATTEMPTS")

    # Security Headers
    SECURITY_ENABLE_CSP: bool = Field(default=True, env="SECURITY_ENABLE_CSP")
    SECURITY_ENABLE_HSTS: bool = Field(default=True, env="SECURITY_ENABLE_HSTS")
    SECURITY_FRAME_OPTIONS: str = Field(default="DENY", env="SECURITY_FRAME_OPTIONS")
    SECURITY_CONTENT_TYPE_NOSNIFF: bool = Field(default=True, env="SECURITY_CONTENT_TYPE_NOSNIFF")
    SECURITY_XSS_PROTECTION: bool = Field(default=True, env="SECURITY_XSS_PROTECTION")

    # CORS Configuration (Strict)
    CORS_ORIGINS: List[str] = Field(
        default=["https://lms.sashainfinity.com", "https://sashainfinity.com", "https://backend.sashainfinity.com", "https://meiporul.sashainfinity.com", "https://seyappaduporul.sashainfinity.com", "https://utporul.sashainfinity.com", "http://localhost:3100", "http://127.0.0.1:3100", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["lms.sashainfinity.com", "backend.sashainfinity.com", "meiporul.sashainfinity.com", "seyappaduporul.sashainfinity.com", "utporul.sashainfinity.com", "localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )

    # API Security
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    ENABLE_API_RATE_LIMITING: bool = Field(default=True, env="ENABLE_API_RATE_LIMITING")
    ENABLE_REQUEST_LOGGING: bool = Field(default=True, env="ENABLE_REQUEST_LOGGING")
    ENABLE_SECURITY_HEADERS: bool = Field(default=True, env="ENABLE_SECURITY_HEADERS")

    # File Upload Security
    UPLOAD_PATH: str = Field(default="./uploads", env="UPLOAD_PATH")
    MAX_FILE_SIZE: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB instead of 100MB
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"],
        env="ALLOWED_EXTENSIONS"
    )
    SCAN_UPLOADED_FILES: bool = Field(default=True, env="SCAN_UPLOADED_FILES")
    QUARANTINE_INFECTED_FILES: bool = Field(default=True, env="QUARANTINE_INFECTED_FILES")

    # IP Security
    ALLOWED_IP_RANGES: List[str] = Field(
        default=[],  # Empty means allow all, specify ranges for admin access
        env="ALLOWED_IP_RANGES"
    )
    BLOCKED_IP_RANGES: List[str] = Field(
        default=[],
        env="BLOCKED_IP_RANGES"
    )
    ENABLE_IP_WHITELISTING: bool = Field(default=False, env="ENABLE_IP_WHITELISTING")

    # Monitoring and Logging
    ENABLE_SECURITY_MONITORING: bool = Field(default=True, env="ENABLE_SECURITY_MONITORING")
    LOG_FAILED_LOGIN_ATTEMPTS: bool = Field(default=True, env="LOG_FAILED_LOGIN_ATTEMPTS")
    LOG_SUSPICIOUS_ACTIVITIES: bool = Field(default=True, env="LOG_SUSPICIOUS_ACTIVITIES")
    ALERT_ON_SECURITY_EVENTS: bool = Field(default=True, env="ALERT_ON_SECURITY_EVENTS")
    SECURITY_ALERT_EMAIL: str = Field(default="admin@sashainfinity.com", env="SECURITY_ALERT_EMAIL")

    # Payment (Razorpay)
    RAZORPAY_KEY: str = Field(default="", env="RAZORPAY_KEY")
    RAZORPAY_SECRET: str = Field(default="", env="RAZORPAY_SECRET")
    RAZORPAY_KEY_ID: str = Field(default="", env="RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: str = Field(default="", env="RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: str = Field(default="", env="RAZORPAY_WEBHOOK_SECRET")

    # Edgyy Payment Proxy
    EDGYY_SECRET_TOKEN: str = Field(default="", env="EDGYY_SECRET_TOKEN")
    EDGYY_WEBHOOK_URL: str = Field(default="https://edgyy.in/api/v1/payments/webhook/", env="EDGYY_WEBHOOK_URL")
    EDGYY_WEBHOOK_SECRET: str = Field(default="", env="EDGYY_WEBHOOK_SECRET")

    # Email
    SMTP_HOST: str = Field(default="", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field(default="noreply@sashainfinity.com", env="EMAIL_FROM")
    # Operational alerts (payment pipeline). Empty falls back to EMAIL_FROM.
    ADMIN_EMAIL: str = Field(default="", env="ADMIN_EMAIL")

    # Meta WhatsApp Cloud API. Secrets are consumed only by the server and are
    # never included in the public configuration-status response.
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="", env="WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = Field(
        default="", env="WHATSAPP_BUSINESS_ACCOUNT_ID"
    )
    WHATSAPP_BUSINESS_PHONE: str = Field(default="", env="WHATSAPP_BUSINESS_PHONE")
    WHATSAPP_ACCESS_TOKEN: str = Field(default="", env="WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_APP_SECRET: str = Field(default="", env="WHATSAPP_APP_SECRET")
    WHATSAPP_VERIFY_TOKEN: str = Field(default="", env="WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_API_VERSION: str = Field(default="v23.0", env="WHATSAPP_API_VERSION")
    WHATSAPP_APPROVED_TEMPLATES: str = Field(
        default="campus_announcement,attendance_alert,assignment_due",
        env="WHATSAPP_APPROVED_TEMPLATES",
    )

    # Seller (company invoicing) — stamped on all invoices
    SELLER_GSTIN: str = Field(default="", env="SELLER_GSTIN")
    SELLER_LEGAL_NAME: str = Field(default="", env="SELLER_LEGAL_NAME")
    SELLER_ADDRESS: str = Field(default="", env="SELLER_ADDRESS")
    SELLER_STATE_CODE: str = Field(default="", env="SELLER_STATE_CODE")
    GST_RATE_PERCENT: float = Field(default=18.0, env="GST_RATE_PERCENT")

    # Instructor payouts (spec 2026-09-04-money-ops §4): smallest withdrawal an
    # instructor may request, in rupees. Money moves manually (NEFT/UPI); this
    # only keeps the admin queue free of trivial requests.
    MIN_WITHDRAWAL_INR: int = Field(default=500, env="MIN_WITHDRAWAL_INR")

    # URLs
    FRONTEND_URL: str = Field(default="https://lms.sashainfinity.com", env="FRONTEND_URL")
    BACKEND_URL: str = Field(default="https://backend.sashainfinity.com", env="BACKEND_URL")
    DOMAIN: str = Field(default="sashainfinity.com", env="DOMAIN")

    # Logging
    LOG_LEVEL: str = Field(default="WARNING", env="LOG_LEVEL")
    SECURITY_LOG_LEVEL: str = Field(default="INFO", env="SECURITY_LOG_LEVEL")
    LOG_FILE_PATH: str = Field(default="/var/log/sasha_lms", env="LOG_FILE_PATH")

    # Bunny CDN (for video streaming only)
    BUNNY_LIBRARY_ID: str = Field(default="618286", env="BUNNY_LIBRARY_ID")
    BUNNY_API_KEY: str = Field(default="", env="BUNNY_API_KEY")
    BUNNY_CDN_HOSTNAME: str = Field(default="vz-60dda74a-f32.b-cdn.net", env="BUNNY_CDN_HOSTNAME")

    # Live Classes (self-hosted Jitsi) — see docs/LIVE_CLASSES.md.
    # JITSI_JWT_SECRET is dedicated and must NEVER equal JWT_SECRET; blank in
    # dev/tests is fine, but production fails fast (see app/main.py lifespan).
    JITSI_PUBLIC_URL: str = Field(default="", env="JITSI_PUBLIC_URL")
    JITSI_JWT_APP_ID: str = Field(default="sashainfinity", env="JITSI_JWT_APP_ID")
    JITSI_JWT_SECRET: str = Field(default="", env="JITSI_JWT_SECRET")
    # When the Jitsi server does NOT share our JWT secret (e.g. dev using
    # the public meet.jit.si), sending our token makes prosody demand a
    # password (connection.passwordRequired). Servers can't validate it, so
    # omit it and join anonymously — room names are unguessable.
    JITSI_SEND_JWT: bool = Field(default=True, env="JITSI_SEND_JWT")
    JITSI_RECORDINGS_DIR: str = Field(default="recordings_live", env="JITSI_RECORDINGS_DIR")
    # Recording lessons: the optional ASR runtime is separate from the API environment.
    TRANSCRIPTION_PROVIDER: str = "self_hosted"
    TRANSCRIPTION_PYTHON: str = ""
    TRANSCRIPTION_MODEL_PATH: str = ""
    TRANSCRIPTION_DEVICE: str = "cpu"
    TRANSCRIPTION_COMPUTE_TYPE: str = "int8"
    # Shared secret for the internal recording-ingest endpoint
    # (POST /api/v1/internal/live/recordings) — see live_class_internal.py.
    INTERNAL_TOKEN: str = Field(default="", env="INTERNAL_TOKEN")
    # Dedicated credential for the isolated Utporul code judge. It must not
    # reuse JWT_SECRET or INTERNAL_TOKEN in production.
    CODE_RUNNER_TOKEN: str = Field(default="", env="CODE_RUNNER_TOKEN")
    DEFAULT_TIMEZONE: str = Field(default="Asia/Kolkata", env="DEFAULT_TIMEZONE")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore'

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings instance (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
