-- PostgreSQL creation parity for Alembic 0024-0026. Additive; no content is replaced.
-- Existing installations with old transfer foreign keys must also run Alembic 0026.
-- Prefer `alembic upgrade head` for tracked installations.
CREATE TABLE IF NOT EXISTS service_heartbeats (
    name VARCHAR(64) PRIMARY KEY, status VARCHAR(24) NOT NULL,
    detail JSON NOT NULL, seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS course_transfers (
    id VARCHAR(36) PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(20) NOT NULL, filename VARCHAR(255) NOT NULL,
    sha256 VARCHAR(64) NOT NULL, manifest JSON NOT NULL, warnings JSON NOT NULL,
    status VARCHAR(20) NOT NULL, course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL, error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ NOT NULL,
    staging_cleaned_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_course_transfers_owner_id ON course_transfers(owner_id);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS enabled_tools JSON;
ALTER TABLE course_transfers ADD COLUMN IF NOT EXISTS staging_cleaned_at TIMESTAMPTZ;
