-- Admin messages: record whether the message was actually emailed.
--
-- Before this, `POST /api/v1/admin/messages/bulk` only inserted rows into
-- admin_messages, so the admin UI listed the message under "Recently sent"
-- while no email ever left the server. The router now emails each recipient
-- and stores the outcome here.
--
-- Values: 'sent' | 'failed' | 'no_email'. NULL means the row predates emailing.
--
-- Also applied automatically by ensure_schema() in app/core/database.py.

ALTER TABLE admin_messages ADD COLUMN IF NOT EXISTS email_status VARCHAR(20);
