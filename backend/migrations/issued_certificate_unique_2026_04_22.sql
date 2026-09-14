-- Idempotency guard for IssuedCertificate.
-- Enforces: one certificate per (user_id, course_id).
--
-- Problem: two concurrent completion-triggers (e.g. one from mark-lesson-complete
-- and one from a video-progress auto-detect in another worker) could both insert
-- an IssuedCertificate row before either commit. The application-level
-- "query-before-insert" check doesn't protect across workers.
--
-- This migration:
--  1. Deletes duplicate rows, keeping the oldest (smallest id) per (user, course).
--     The oldest row is the one that was live longest and whose certificate_hash
--     was most likely shared with the user via email / cert URL.
--  2. Adds the UNIQUE index.
--
-- Run AFTER pulling the corresponding code change.  On Postgres the constraint
-- is a plain UNIQUE; the app code catches IntegrityError and retries the
-- select to resolve the winner.

BEGIN;

-- 1. Dedupe existing rows (keep oldest, delete the rest).
DELETE FROM issued_certificates ic1
USING issued_certificates ic2
WHERE ic1.user_id = ic2.user_id
  AND ic1.course_id = ic2.course_id
  AND ic1.id > ic2.id;

-- 2. Add the unique constraint if it doesn't exist.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_issued_certificate_user_course'
    ) THEN
        ALTER TABLE issued_certificates
        ADD CONSTRAINT uq_issued_certificate_user_course
        UNIQUE (user_id, course_id);
    END IF;
END
$$;

-- 3. Supporting btree index for the common (user_id, course_id) lookup.
CREATE INDEX IF NOT EXISTS ix_issued_cert_user_course
    ON issued_certificates (user_id, course_id);

COMMIT;
