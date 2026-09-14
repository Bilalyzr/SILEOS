-- 2026-04-23: Ensure course_reviews has a `status` column used for moderation.
-- The current model has `review_status` (default 'approved'). This migration
-- ADDS `status` as the canonical moderation column. New rows default to
-- 'pending' at the ORM level; existing rows default to 'approved' here so
-- they remain visible after deployment.
ALTER TABLE course_reviews
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved';

ALTER TABLE course_reviews
    ADD COLUMN IF NOT EXISTS admin_notes TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS ix_course_reviews_status ON course_reviews (status);
