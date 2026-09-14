-- Add cohort_id foreign key to coupons table
-- Idempotent: the pipeline's migration ledger was never baselined, so files
-- already applied by hand must also succeed when the pipeline replays them.
BEGIN;

ALTER TABLE coupons
ADD COLUMN IF NOT EXISTS cohort_id INTEGER REFERENCES cohorts(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_coupon_cohort ON coupons(cohort_id);

-- Add comment for documentation
COMMENT ON COLUMN coupons.cohort_id IS 'Links coupon to a cohort for SPOC referral tracking';

COMMIT;
