-- Memberships sub-project. Fresh DBs get these from init_db(); run manually
-- against existing Postgres:
--   docker-compose exec postgres psql -U tutor -d tutor_lms -f /path/to/this.sql

CREATE TABLE IF NOT EXISTS membership_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT DEFAULT '',
    all_access BOOLEAN NOT NULL DEFAULT FALSE,
    period VARCHAR(20) NOT NULL,
    interval INTEGER NOT NULL DEFAULT 1,
    price NUMERIC(10,2) NOT NULL,
    grace_days INTEGER NOT NULL DEFAULT 7,
    razorpay_plan_id VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS membership_plan_courses (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES membership_plans(id),
    course_id INTEGER NOT NULL REFERENCES courses(id)
);
CREATE INDEX IF NOT EXISTS ix_membership_plan_courses_plan_id
    ON membership_plan_courses (plan_id);

CREATE TABLE IF NOT EXISTS memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER NOT NULL REFERENCES membership_plans(id),
    razorpay_subscription_id VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    current_period_end TIMESTAMPTZ,
    grace_until TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_memberships_user_id ON memberships (user_id);
CREATE INDEX IF NOT EXISTS ix_memberships_subscription
    ON memberships (razorpay_subscription_id);

-- At most one blocking (PENDING/ACTIVE/GRACE) membership per user. Closes the
-- read-then-insert race in POST /api/v1/memberships/subscribe; the loser of a
-- concurrent double-submit gets an IntegrityError -> 409.
-- NOTE: apply AFTER de-duplicating any existing blocking rows, e.g.
--   SELECT user_id FROM memberships WHERE status IN ('PENDING','ACTIVE','GRACE')
--   GROUP BY user_id HAVING COUNT(*) > 1;
CREATE UNIQUE INDEX IF NOT EXISTS uq_memberships_one_blocking_per_user
    ON memberships (user_id) WHERE status IN ('PENDING','ACTIVE','GRACE');

ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS enrollment_source VARCHAR(20);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS membership_id INTEGER REFERENCES memberships(id);
CREATE INDEX IF NOT EXISTS ix_enrollments_membership_id
    ON enrollments (membership_id);
