-- Admin "View as Instructor" impersonation audit log.
--
-- Every time an admin starts an impersonation session we insert one row.
-- `ended_at` is populated either when the admin explicitly exits, or
-- lazily when the 30-minute impersonation token is observed to have
-- expired. We never UPDATE the started_at / admin_user_id / target_user_id
-- after insert — those are audit-immutable.
--
-- Indexes: queries fan out on admin ("who did admin X impersonate?") and
-- on target ("who has instructor Y been impersonated by?"). Both columns
-- get their own single-column index.

CREATE TABLE IF NOT EXISTS admin_impersonation_logs (
    id               SERIAL PRIMARY KEY,
    admin_user_id    INTEGER NOT NULL,
    target_user_id   INTEGER NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at         TIMESTAMPTZ NULL,
    reason           TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_admin_impersonation_logs_admin_user_id
    ON admin_impersonation_logs (admin_user_id);

CREATE INDEX IF NOT EXISTS ix_admin_impersonation_logs_target_user_id
    ON admin_impersonation_logs (target_user_id);

-- FKs wrapped in DO-blocks so re-running the migration is idempotent.
-- NOT VALID: adding the constraint must not validate historical rows —
-- logs referencing since-deleted users would abort the deploy. New and
-- updated rows are still fully enforced.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_admin_impersonation_admin_user'
    ) THEN
        ALTER TABLE admin_impersonation_logs
            ADD CONSTRAINT fk_admin_impersonation_admin_user
            FOREIGN KEY (admin_user_id) REFERENCES users(id) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_admin_impersonation_target_user'
    ) THEN
        ALTER TABLE admin_impersonation_logs
            ADD CONSTRAINT fk_admin_impersonation_target_user
            FOREIGN KEY (target_user_id) REFERENCES users(id) NOT VALID;
    END IF;
END $$;
