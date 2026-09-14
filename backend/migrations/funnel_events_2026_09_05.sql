-- R1 conversion funnel. Parity with Alembic 0015.
CREATE TABLE IF NOT EXISTS funnel_events (
  id SERIAL PRIMARY KEY, kind VARCHAR(24) NOT NULL, course_id INTEGER NOT NULL REFERENCES courses(id),
  user_id INTEGER REFERENCES users(id), session_id VARCHAR(64) NOT NULL, meta JSON, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_funnel_events_kind ON funnel_events(kind);
CREATE INDEX IF NOT EXISTS ix_funnel_events_course_id ON funnel_events(course_id);
CREATE INDEX IF NOT EXISTS ix_funnel_events_user_id ON funnel_events(user_id);
CREATE INDEX IF NOT EXISTS ix_funnel_events_session_id ON funnel_events(session_id);
CREATE INDEX IF NOT EXISTS ix_funnel_events_created_at ON funnel_events(created_at);
