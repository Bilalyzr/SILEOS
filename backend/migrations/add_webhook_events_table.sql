-- Payment Reliability Core: webhook inbox.
-- init_db() creates this automatically on fresh databases; run this file
-- manually against existing production Postgres:
--   docker-compose exec postgres psql -U tutor -d tutor_lms -f /path/to/this.sql

CREATE TABLE IF NOT EXISTS webhook_events (
    id              SERIAL PRIMARY KEY,
    event_id        VARCHAR(255) NOT NULL UNIQUE,
    event_type      VARCHAR(100) NOT NULL DEFAULT '',
    payload         JSON NOT NULL DEFAULT '{}',
    signature_valid BOOLEAN NOT NULL DEFAULT FALSE,
    status          VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    last_error      TEXT,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_webhook_events_event_id ON webhook_events (event_id);
CREATE INDEX IF NOT EXISTS ix_webhook_events_status ON webhook_events (status);

-- The gateway payment id is the pipeline's idempotency key; this constraint is
-- what makes a true concurrent /verify-vs-webhook race resolve to one winner
-- instead of double-booking. Partial: legacy/non-gateway rows default to ''.
CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_gateway_payment_id
    ON payments (gateway_payment_id) WHERE gateway_payment_id <> '';
