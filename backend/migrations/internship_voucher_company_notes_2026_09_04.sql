-- Migration: internship_vouchers company notes + engagement status
-- Date: 2026-09-04
-- Adds:
--   * internship_vouchers.company_notes (private notes, company-editable)
--   * internship_vouchers.engagement_status ('active'|'completed'|'closed';
--     company-facing placement status, distinct from the existing `status`
--     column which tracks voucher redemption ('issued'/'redeemed') and must
--     never be written by the company dashboard)
--
-- Idempotent — safe to re-run.
BEGIN;

ALTER TABLE internship_vouchers
    ADD COLUMN IF NOT EXISTS company_notes     TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS engagement_status VARCHAR(20) NOT NULL DEFAULT 'active';

COMMIT;
