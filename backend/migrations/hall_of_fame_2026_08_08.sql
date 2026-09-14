-- Hall of Fame - editable staff showcase managed by admins/superadmins.
--
-- Stores the staff profiles that appear on the public /hall-of-fame page.
-- Replaces the hardcoded HALL_OF_FAME array that lived in the frontend.
-- Admins CRUD these rows via /api/v1/hall-of-fame/* endpoints.
--
-- Idempotent: safe to re-run. PostgreSQL syntax.

BEGIN;

CREATE TABLE IF NOT EXISTS hall_of_fame_members (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    role         VARCHAR(200) NOT NULL DEFAULT '',
    company      VARCHAR(200) NOT NULL DEFAULT '',
    photo        VARCHAR(500),
    tenure       VARCHAR(100) NOT NULL DEFAULT '',
    location     VARCHAR(200),
    linkedin     VARCHAR(500),
    blurb        TEXT,
    highlight    VARCHAR(100),
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_hall_of_fame_sort_order
    ON hall_of_fame_members (sort_order);

CREATE INDEX IF NOT EXISTS ix_hall_of_fame_is_published
    ON hall_of_fame_members (is_published);

COMMIT;
