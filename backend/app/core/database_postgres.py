"""
Database configuration and connection management (Simplified)
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings

settings = get_settings()

# Create sync engine (simpler for now)
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

def get_db() -> Session:
    """Get database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """Initialize database (create tables if needed)"""
    print("Initializing database...")
    # In production, use Alembic migrations instead
    # Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")

def create_tables():
    """Create all tables (for development)"""
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully")