-- fix_coupons_constraints.sql — 2026-08-24
--
-- Incident: coupon management 400'd on GET /api/v1/coupons/ because three
-- bulk-seeded rows (WELCOME10, SAVE500, NEWYEAR50) had usage_count NULL and
-- CouponListResponse declares usage_count: int. The table also had NO primary
-- key and NO unique(code), so a double-run of a seed had silently inserted an
-- exact duplicate of almost every coupon (383 rows / 193 ids).
--
-- Applied live to production 2026-08-24. Re-run-safe guards included so this
-- file can be applied to dev/test clones created before the fix.

BEGIN;

-- 1. Backfill NULL counters (the original 400 trigger)
UPDATE coupons SET usage_count = 0 WHERE usage_count IS NULL;

-- 2. Drop exact duplicate rows, keeping one row per id
DELETE FROM coupons a
 USING coupons b
 WHERE a.ctid > b.ctid AND a.id = b.id;

-- 3. Add the constraints that were missing from day one (guarded)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'coupons_pkey') THEN
    ALTER TABLE coupons ADD CONSTRAINT coupons_pkey PRIMARY KEY (id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'coupons_code_unique') THEN
    ALTER TABLE coupons ADD CONSTRAINT coupons_code_unique UNIQUE (code);
  END IF;
END $$;

-- 4. usage_count can never be NULL again
ALTER TABLE coupons ALTER COLUMN usage_count SET DEFAULT 0;
ALTER TABLE coupons ALTER COLUMN usage_count SET NOT NULL;

COMMIT;
