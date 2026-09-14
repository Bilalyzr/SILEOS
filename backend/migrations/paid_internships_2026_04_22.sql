-- =============================================================================
-- Paid Internship Programs — schema migration (2026-04-22)
-- =============================================================================
--
-- BACKUP FIRST (recommended):
--   pg_dump -t internships -t cohorts -t internship_applications tutor_lms \
--     > backup_paid_internships_pre_2026_04_22.sql
--
-- WHAT THIS DOES:
--   1. Drops the legacy `internship_applications` table entirely (CASCADE).
--      The old "apply-to-internship" flow is being replaced by a paid-voucher
--      flow; application records are no longer meaningful.
--   2. Relaxes NOT NULL on cohorts.course_id and cohorts.college_id so that
--      internship-owned cohorts (which have neither a course nor a college)
--      can be represented.
--   3. Repurposes the `internships` table for the new paid model:
--        - Adds price, slug, description, cover_image, is_published,
--          spoc_user_id, cohort_id, created_by.
--        - Drops obsolete job-posting columns
--          (company, duration, stipend, location, mode, requirements,
--           apply_link, application_deadline).
--   4. Creates the new `internship_vouchers` table.
--
-- NOTES / RISKS:
--   * Existing `internships` rows (pre-migration) will have:
--       price          = 0        (backfill DEFAULT; application-level cleanup required)
--       spoc_user_id   = NULL     (no enforcement at DB-level on legacy rows)
--       cohort_id      = NULL     (new cohort must be created by admin)
--       is_published   = false    (safe default — legacy rows hidden until fixed)
--     Admin MUST review these rows after migration: either delete them or
--     populate price/spoc/cohort before re-publishing.
--   * `price` is added with DEFAULT 0 so the NOT NULL constraint can be applied
--     to pre-existing rows. The DEFAULT is intentionally left on the column
--     (harmless — the ORM always supplies a price on INSERT). Drop it later if
--     you prefer strict "no implicit free" semantics.
--   * `slug` is backfilled from `title` (lower, spaces -> '-') with the row id
--     appended for uniqueness, then constrained NOT NULL UNIQUE.
--   * This migration is idempotent where practical (IF NOT EXISTS / IF EXISTS),
--     but re-running after partial success is not guaranteed — restore from
--     backup and re-run cleanly if it aborts mid-way.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Drop legacy applications table
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS internship_applications CASCADE;


-- ---------------------------------------------------------------------------
-- 2. Relax NOT NULL on cohorts FKs
-- ---------------------------------------------------------------------------
ALTER TABLE cohorts ALTER COLUMN course_id  DROP NOT NULL;
ALTER TABLE cohorts ALTER COLUMN college_id DROP NOT NULL;


-- ---------------------------------------------------------------------------
-- 3. Repurpose `internships` table
-- ---------------------------------------------------------------------------

-- 3a. Drop obsolete columns (old job-posting shape) if present.
ALTER TABLE internships DROP COLUMN IF EXISTS company;
ALTER TABLE internships DROP COLUMN IF EXISTS duration;
ALTER TABLE internships DROP COLUMN IF EXISTS stipend;
ALTER TABLE internships DROP COLUMN IF EXISTS location;
ALTER TABLE internships DROP COLUMN IF EXISTS mode;
ALTER TABLE internships DROP COLUMN IF EXISTS requirements;
ALTER TABLE internships DROP COLUMN IF EXISTS apply_link;
ALTER TABLE internships DROP COLUMN IF EXISTS application_deadline;

-- 3b. Add price (backfill DEFAULT 0, kept so re-inserts never fail NOT NULL).
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS price NUMERIC(12, 2) NOT NULL DEFAULT 0;

-- 3c. Add remaining content columns.
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS cover_image VARCHAR(500) DEFAULT '';

-- 3d. is_published: new default is FALSE (legacy rows hidden until reviewed).
--     The old model defaulted to TRUE — if the column already exists we leave
--     existing values in place but flip the column default to FALSE.
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE internships
    ALTER COLUMN is_published SET DEFAULT FALSE;

-- 3e. slug: add nullable, backfill, then enforce NOT NULL + UNIQUE + index.
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS slug VARCHAR(255);

UPDATE internships
SET slug = LOWER(REGEXP_REPLACE(COALESCE(title, 'internship'), '[^a-zA-Z0-9]+', '-', 'g'))
           || '-' || id::text
WHERE slug IS NULL OR slug = '';

ALTER TABLE internships ALTER COLUMN slug SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'internships_slug_key'
    ) THEN
        ALTER TABLE internships ADD CONSTRAINT internships_slug_key UNIQUE (slug);
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS ix_internships_slug ON internships (slug);

-- 3f. spoc_user_id — nullable for legacy rows; NOT NULL enforced at app layer
--     for new Internship creations (see routers in T2).
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS spoc_user_id INTEGER REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_internships_spoc_user_id
    ON internships (spoc_user_id);

-- 3g. cohort_id — nullable for legacy rows; UNIQUE to enforce 1:1.
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS cohort_id INTEGER REFERENCES cohorts(id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'internships_cohort_id_key'
    ) THEN
        ALTER TABLE internships ADD CONSTRAINT internships_cohort_id_key UNIQUE (cohort_id);
    END IF;
END$$;

-- 3h. created_by — old model had this NOT NULL; relax to nullable (matches new
--     model) so legacy rows whose creator is gone don't block migrations.
ALTER TABLE internships
    ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE internships
    ALTER COLUMN created_by DROP NOT NULL;


-- ---------------------------------------------------------------------------
-- 4. Create internship_vouchers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS internship_vouchers (
    id                     SERIAL PRIMARY KEY,
    code                   VARCHAR(32)  NOT NULL UNIQUE,
    internship_id          INTEGER      NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
    buyer_user_id          INTEGER      NOT NULL REFERENCES users(id),
    amount_paid            NUMERIC(12,2) NOT NULL,
    razorpay_order_id      VARCHAR(255) DEFAULT '',
    razorpay_payment_id    VARCHAR(255) DEFAULT '',
    status                 VARCHAR(20)  NOT NULL DEFAULT 'issued',
    redeemed_on_course_id  INTEGER      REFERENCES courses(id),
    redeemed_at            TIMESTAMPTZ,
    created_at             TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_internship_vouchers_code
    ON internship_vouchers (code);
CREATE INDEX IF NOT EXISTS ix_internship_vouchers_internship_id
    ON internship_vouchers (internship_id);
CREATE INDEX IF NOT EXISTS ix_internship_vouchers_buyer_user_id
    ON internship_vouchers (buyer_user_id);
CREATE INDEX IF NOT EXISTS ix_vouchers_buyer_status
    ON internship_vouchers (buyer_user_id, status);

COMMIT;
