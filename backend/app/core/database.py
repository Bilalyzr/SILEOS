"""
Database configuration and connection management
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# PostgreSQL connection pool settings
is_postgres = "postgresql" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    # Pool settings (PostgreSQL only)
    pool_size=10,               # Maintain 10 persistent connections
    max_overflow=20,            # Allow 20 extra connections under load
    pool_pre_ping=True,         # Test connection before using (fixes dropped connections)
    pool_recycle=1800,          # Recycle connections every 30 min (prevents stale connections)
    pool_timeout=30,            # Wait up to 30s for a connection from pool
) if is_postgres else create_engine(
    DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_schema():
    """
    Idempotently reconcile known schema drift.

    `create_all` adds missing *tables* but never missing *columns*, so when a
    column is added to a model after its table already exists (the recurring
    "UndefinedColumn 500" problem on this project), the table stays behind and
    every query against that model 500s. These statements bring drift-prone
    tables back in line and backfill NULL timestamps that would otherwise fail
    strict response schemas. Each runs in its own transaction so one failure
    can't abort the rest. Postgres-only (uses ADD COLUMN IF NOT EXISTS).
    """
    if not is_postgres:
        return

    statements = [
        # courses — columns added to the model after the initial deploy
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS num_offline_workshops INTEGER DEFAULT 0",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS num_hours INTEGER DEFAULT 0",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS institution VARCHAR(255) DEFAULT ''",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS course_type VARCHAR(50) DEFAULT ''",
        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS geogebra_applet_id INTEGER",
        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS three_d_model_id INTEGER",
        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS virtual_lab_sim VARCHAR(50)",
        "ALTER TABLE three_d_models ADD COLUMN IF NOT EXISTS is_library BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS purpose VARCHAR(24)",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS mode VARCHAR(24)",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS audience VARCHAR(16)",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_policy VARCHAR(12)",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_deleted_at TIMESTAMPTZ",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_deleted_by INTEGER",
        "ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_delete_reason VARCHAR(300)",
        "ALTER TABLE user_game_stats ADD COLUMN IF NOT EXISTS streak_freeze_month VARCHAR(7)",
        "ALTER TABLE user_game_stats ADD COLUMN IF NOT EXISTS streak_freezes_used INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_template BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS razorpay_offer_id VARCHAR(64)",
        "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS quiz_available_from TIMESTAMPTZ",
        "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS quiz_available_until TIMESTAMPTZ",
        "ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS is_retired BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE three_d_models ADD COLUMN IF NOT EXISTS tier_files JSON",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS enabled_tools JSON",
        "ALTER TABLE games ADD COLUMN IF NOT EXISTS is_listed BOOLEAN DEFAULT 0",
        "CREATE TABLE IF NOT EXISTS type_profiles (type VARCHAR(20) PRIMARY KEY, label VARCHAR(100), default_enabled_tools JSON, default_assessment_weights JSON, learner_path_template JSON)",
        "ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS interactive_modules JSON DEFAULT '[]'",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS total_reviews INTEGER DEFAULT 0",
        # total times any lesson video in a course has been viewed
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS video_view_count INTEGER DEFAULT 0",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS certificate_design JSON DEFAULT '{}'::json",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()",
        "ALTER TABLE courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()",
        # backfill NULL timestamps so admin/course responses don't 500
        "UPDATE courses SET created_at = now() WHERE created_at IS NULL",
        "UPDATE courses SET updated_at = now() WHERE updated_at IS NULL",
        # assignment_submissions — approver audit trail (instructor vs admin)
        "ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS graded_by INTEGER",
        "ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS graded_by_role VARCHAR(20)",
        # admin_messages — email delivery outcome per recipient
        "ALTER TABLE admin_messages ADD COLUMN IF NOT EXISTS email_status VARCHAR(20)",
    ]

    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception as e:
            print(f"[ensure_schema] skipped ({e}): {stmt[:70]}")


async def init_db():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    # Self-heal known column drift on existing tables (create_all won't).
    ensure_schema()
    print("Database initialized successfully")

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully")
