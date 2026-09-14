"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET: str = Field(..., env="JWT_SECRET", default="")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://sashainfinity.com"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "sashainfinity.com"],
        env="ALLOWED_HOSTS"
    )

    # Payment (Razorpay)
    RAZORPAY_KEY_ID: str = Field(..., env="RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: str = Field(..., env="RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: str = Field(..., env="RAZORPAY_WEBHOOK_SECRET")

    # File Upload
    UPLOAD_PATH: str = Field(default="./uploads", env="UPLOAD_PATH")
    MAX_FILE_SIZE: int = Field(default=104857600, env="MAX_FILE_SIZE")  # 100MB
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "pdf", "mp4", "mov", "avi", "mkv"],
        env="ALLOWED_EXTENSIONS"
    )

    # Email
    SMTP_HOST: str = Field(default="", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field(default="noreply@sashainfinity.com", env="EMAIL_FROM")

    # URLs
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    BACKEND_URL: str = Field(default="http://localhost:8000", env="BACKEND_URL")
    DOMAIN: str = Field(default="sashainfinity.com", env="DOMAIN")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings instance (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings