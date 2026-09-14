-- 2026-08-13: Watch-session log for Student Activity (Issue 8).
-- One row per video-watch segment (play / pause / resume / completed).
-- Aggregated by the admin Student Activity endpoints to report time spent,
-- number of sessions, last-active and the full viewing history.
-- Safe to re-run (CREATE TABLE IF NOT EXISTS).
CREATE TABLE IF NOT EXISTS watch_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    event VARCHAR(20) NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    position_seconds INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_watch_sessions_user_id ON watch_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_watch_sessions_course_id ON watch_sessions (course_id);
CREATE INDEX IF NOT EXISTS ix_watch_sessions_lesson_id ON watch_sessions (lesson_id);
CREATE INDEX IF NOT EXISTS ix_watch_sessions_started_at ON watch_sessions (started_at);
CREATE INDEX IF NOT EXISTS ix_watch_sessions_user_course ON watch_sessions (user_id, course_id);
