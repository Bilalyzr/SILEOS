-- Add cohort_id foreign key to enrollments table
-- Idempotent: the pipeline's migration ledger was never baselined, so files
-- already applied by hand must also succeed when the pipeline replays them.
BEGIN;

ALTER TABLE enrollments
ADD COLUMN IF NOT EXISTS cohort_id INTEGER REFERENCES cohorts(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_enrollment_cohort ON enrollments(cohort_id);

-- Add comment for documentation
COMMENT ON COLUMN enrollments.cohort_id IS 'Tracks which cohort (if any) student enrolled through';

COMMIT;
