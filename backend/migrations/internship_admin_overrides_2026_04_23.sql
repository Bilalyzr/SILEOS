-- Migration: internship admin overrides
-- Date: 2026-04-23
-- Adds:
--   * internship_attendance table (per-student per-day attendance)
--   * internship_vouchers.hired_by_company_id + override metadata (manual
--     hiring assignment by admin)
--
-- Idempotent — safe to re-run.
BEGIN;

-- -----------------------------------------------------------------------------
-- internship_attendance
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS internship_attendance (
    id               SERIAL PRIMARY KEY,
    internship_id    INTEGER NOT NULL REFERENCES internships(id),
    user_id          INTEGER NOT NULL REFERENCES users(id),
    attended_at      DATE NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'present',
    notes            TEXT DEFAULT '',
    marked_by        INTEGER REFERENCES users(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_internship_attendance_internship_id
    ON internship_attendance (internship_id);
CREATE INDEX IF NOT EXISTS ix_internship_attendance_user_id
    ON internship_attendance (user_id);
CREATE INDEX IF NOT EXISTS ix_internship_attendance_internship_date
    ON internship_attendance (internship_id, attended_at);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'uq_internship_attendance_internship_user_date'
    ) THEN
        ALTER TABLE internship_attendance
            ADD CONSTRAINT uq_internship_attendance_internship_user_date
            UNIQUE (internship_id, user_id, attended_at);
    END IF;
END$$;

-- -----------------------------------------------------------------------------
-- internship_vouchers — admin hiring override columns
-- -----------------------------------------------------------------------------
ALTER TABLE internship_vouchers
    ADD COLUMN IF NOT EXISTS hired_by_company_id  INTEGER REFERENCES companies(id),
    ADD COLUMN IF NOT EXISTS hired_by_override_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS hired_by_override_by INTEGER REFERENCES users(id);

COMMIT;
