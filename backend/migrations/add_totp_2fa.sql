-- Two-factor authentication (TOTP) columns on users.
--
-- This repo has no Alembic; migrations are hand-applied SQL (see
-- backend/migrations/add_coupons_tables.sql for the existing precedent).
-- init_db() only issues CREATE TABLE IF NOT EXISTS, so it will NOT add
-- columns to a table that already exists — this file must be run manually
-- against an existing database.
--
-- Apply with:
--   docker-compose exec -T postgres psql -U tutor -d tutor_lms \
--     -f /path/to/add_totp_2fa.sql
-- or:
--   docker-compose exec -T postgres psql -U tutor -d tutor_lms \
--     < backend/migrations/add_totp_2fa.sql
--
-- Safe to re-run: both statements are IF NOT EXISTS.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Existing rows inherit totp_enabled = FALSE, so nobody is challenged for a
-- code until they have completed enrolment via POST /api/v1/auth/2fa/enable.
-- That is intentional: enabling enforcement for accounts with no registered
-- authenticator would lock them out immediately.
