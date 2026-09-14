"""Alembic migration test: upgrade head + downgrade base against a scratch
SQLite FILE database (not the in-memory `db` fixture — Alembic needs a real
file path in the DATABASE_URL so it can open its own connection independent
of the test's SQLAlchemy session).

Verifies:
  - `alembic upgrade head` creates all seven live-class tables (via
    sqlalchemy.inspect), on top of the full pre-existing app schema.
  - `alembic downgrade base` removes them again (0001 is a no-op stamp, so
    "base" == before the live-class tables existed).
"""
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]

LIVE_CLASS_TABLES = {
    "live_class_schedules",
    "live_classes",
    "live_class_join_tokens",
    "live_class_attendance",
    "live_class_polls",
    "live_class_poll_votes",
    "live_class_events",
}


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    # env.py reads DATABASE_URL from the environment (falls back to
    # settings), so set it directly rather than via set_main_option.
    os.environ["DATABASE_URL"] = db_url
    return cfg


def test_upgrade_head_creates_live_class_tables(tmp_path):
    db_file = tmp_path / "migration_test.sqlite3"
    db_url = f"sqlite:///{db_file}"
    cfg = _alembic_config(db_url)

    try:
        command.upgrade(cfg, "head")

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        missing = LIVE_CLASS_TABLES - tables
        assert not missing, f"missing tables after upgrade: {missing}"

        # 0001 is an intentional no-op stamp (deviations file item 9):
        # pre-existing tables (users, courses, ...) are owned by init_db()/
        # create_all, NOT Alembic, so a bare `alembic upgrade head` against
        # an empty database creates ONLY the live-class tables plus
        # Alembic's own bookkeeping table.
        assert "users" not in tables
        assert "alembic_version" in tables
    finally:
        os.environ.pop("DATABASE_URL", None)


def test_downgrade_base_drops_live_class_tables(tmp_path):
    db_file = tmp_path / "migration_downgrade_test.sqlite3"
    db_url = f"sqlite:///{db_file}"
    cfg = _alembic_config(db_url)

    try:
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        leftover = LIVE_CLASS_TABLES & tables
        assert not leftover, f"live-class tables survived downgrade: {leftover}"
    finally:
        os.environ.pop("DATABASE_URL", None)


def test_upgrade_head_tolerates_create_all_running_first(tmp_path):
    """Reproduces the real deploy ordering: init_db()'s create_all() runs on
    every app startup and nothing currently invokes Alembic beforehand, so
    create_all() usually creates the live-class tables (they're registered
    in app/models/__init__.py) before `alembic upgrade head` ever runs.

    `alembic upgrade head` must be a safe no-op in that case (not raise
    "table already exists"), tables must still be present afterwards, and a
    subsequent `downgrade base` must still cleanly remove them.
    """
    db_file = tmp_path / "migration_create_all_first_test.sqlite3"
    db_url = f"sqlite:///{db_file}"

    # Step 1: simulate init_db() — create_all() against the full app schema,
    # which includes the seven live-class tables since live_class.py is
    # registered in app/models/__init__.py.
    from app.core.database import Base
    from app import models  # noqa: F401  (registers all models on Base.metadata)

    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    cfg = _alembic_config(db_url)
    try:
        # Step 2: alembic upgrade head must succeed (no-op for 0002) rather
        # than raising OperationalError "table already exists".
        command.upgrade(cfg, "head")

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        missing = LIVE_CLASS_TABLES - tables
        assert not missing, f"live-class tables missing after create_all + upgrade: {missing}"

        # Step 3: downgrade must still cleanly remove the tables even though
        # upgrade() didn't create them itself this run.
        command.downgrade(cfg, "base")

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        engine.dispose()

        leftover = LIVE_CLASS_TABLES & tables
        assert not leftover, f"live-class tables survived downgrade: {leftover}"
    finally:
        os.environ.pop("DATABASE_URL", None)
