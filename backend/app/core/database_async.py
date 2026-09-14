"""
Database configuration and connection management
"""
import asyncio
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os
from .config import get_settings

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create sync engine for migrations
sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create sync session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Base class for models
Base = declarative_base()

# Metadata for table creation
metadata = MetaData()

async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    try:
        async with async_engine.begin() as conn:
            # Import all models to register them with SQLAlchemy
            from models import user, course, quiz, enrollment, payment, certificate

            print("📋 Importing all models...")
            print("   ✓ User models (User, UserProfile, InstructorProfile)")
            print("   ✓ Course models (Course, Lesson, Categories, Reviews)")
            print("   ✓ Quiz models (Quiz, Questions, Attempts, Answers)")
            print("   ✓ Enrollment models (Enrollment, Progress, Activities)")
            print("   ✓ Payment models (Orders, Payments, Coupons, Earnings)")
            print("   ✓ Certificate models (Templates, Issued, Verification)")

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Database schema created successfully - SashaInfinity LMS ready!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

async def close_db():
    """Close database connections"""
    await async_engine.dispose()
    print("✅ Database connections closed")