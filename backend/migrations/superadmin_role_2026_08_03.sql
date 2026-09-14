-- SuperAdmin feature — schema additions.
--
-- (1) Add `actor_role` to admin_impersonation_logs so the SuperAdmin audit
--     feed can distinguish superadmin-initiated sessions from ordinary admin
--     ones WITHOUT joining users. Nullable; back-filled to 'admin' for any
--     pre-existing rows so historical sessions read correctly.
-- (2) Supporting indexes for the Phase 3 aggregation queries (per-admin
--     impersonation counts, per-student last-activity, etc.).
--
-- Idempotent: safe to re-run. PostgreSQL syntax (matches the existing
-- admin_impersonation_2026_04_23.sql migration).

-- (1a) actor_role column ---------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'admin_impersonation_logs'
          AND column_name = 'actor_role'
    ) THEN
        ALTER TABLE admin_impersonation_logs
            ADD COLUMN actor_role VARCHAR(32) NULL;
    END IF;
END $$;

-- Back-fill any rows that pre-date this column. Treated as ordinary admin
-- sessions (the only actors that existed before superadmin).
UPDATE admin_impersonation_logs
SET actor_role = 'admin'
WHERE actor_role IS NULL;

-- Index the new column (the audit feed filters on it).
CREATE INDEX IF NOT EXISTS ix_admin_impersonation_logs_actor_role
    ON admin_impersonation_logs (actor_role);

-- (2) Supporting indexes for SuperAdmin monitoring aggregations -----------
-- Existing single-column indexes on admin_user_id / target_user_id cover
-- most point lookups; the composite indexes below speed the dashboard
-- "latest activity" + "open sessions" scans.

-- Quickly find OPEN sessions (ended_at IS NULL) for the overview counter
-- and the audit "open_only" filter.
CREATE INDEX IF NOT EXISTS ix_admin_impersonation_logs_open
    ON admin_impersonation_logs (admin_user_id, started_at DESC)
    WHERE ended_at IS NULL;

-- Per-admin impersonation counts (admins dashboard).
CREATE INDEX IF NOT EXISTS ix_admin_impersonation_logs_admin_started
    ON admin_impersonation_logs (admin_user_id, started_at DESC);
