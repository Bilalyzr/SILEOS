-- 2026-09-19: free membership plans carry no Razorpay object.
-- NOT NULL here turned every free-plan (or gateway-less) creation into a
-- 500 "Internal Error". Apply with:
--   psql -U tutor -d tutor_lms -f migrations/make_razorpay_plan_id_nullable.sql
ALTER TABLE membership_plans ALTER COLUMN razorpay_plan_id DROP NOT NULL;
