-- Add webhook delivery tracking to edgyy_payment_sessions.
--
-- /proxy/webhook (Razorpay payment.captured) is the fail-safe for users who close
-- the browser before /proxy/verify runs. It previously only looked in edgyy_payments,
-- so hosted-session orders were answered "Order not found" and never delivered.
-- The session fallback needs the same idempotency columns edgyy_payments already has,
-- so a delivery that failed during /proxy/verify can still be recovered by the webhook.

ALTER TABLE edgyy_payment_sessions
    ADD COLUMN IF NOT EXISTS webhook_delivered BOOLEAN DEFAULT FALSE;

ALTER TABLE edgyy_payment_sessions
    ADD COLUMN IF NOT EXISTS webhook_delivered_at TIMESTAMP WITH TIME ZONE;

-- Sessions already marked PAID were confirmed to Edgyy via the redirect from
-- /proxy/internal/verify-session, not via webhook. Leave webhook_delivered FALSE so a
-- late Razorpay payment.captured can still re-deliver; Edgyy's receiver is idempotent
-- on registration payment_status.
