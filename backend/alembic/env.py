"""Alembic environment — headless, DATABASE_URL-driven.

Contract (see docs/superpowers/plans/2026-09-02-live-classes.md, Task 2):
  - Reads the `DATABASE_URL` env var; falls back to `settings.DATABASE_URL`
    (app.core.config.get_settings) when unset. This lets `alembic upgrade
    head` / `downgrade base` run against a scratch SQLite file in tests
    (test_live_class_migration.py sets DATABASE_URL before invoking the
    alembic.command API) without touching alembic.ini or requiring Postgres.
  - `target_metadata = Base.metadata` via `from app import models`, so every
    registered model (not just live_class.py) is visible to autogenerate.

Alembic is additive here (deviations file item 9): pre-existing tables are
still owned by init_db()/create_all + backend/migrations/*.sql. Revision
0001 is an empty baseline stamp; 0002 is the only revision that actually
creates/drops tables (the seven live-class tables).
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Make `app.*` importable when alembic is invoked from backend/ or elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so they register on Base.metadata before we hand it to
# Alembic for autogenerate/compare support.
from app import models  # noqa: E402
from app.core.database import Base  # noqa: E402

target_metadata = Base.metadata


def _database_url() -> str:
    """DATABASE_URL env var wins; falls back to settings.DATABASE_URL.

    Keeping env.py independent of alembic.ini's `sqlalchemy.url` (never set
    there) is what lets tests point Alembic at a scratch SQLite file without
    touching the checked-in ini file or requiring Postgres to be reachable.
    """
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    from app.core.config import get_settings

    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
