-- WP6 (v2.0 §4): Studio faces — per-course Parent View / Reward Designer settings + streak freezes. Parity with Alembic 0012.
CREATE TABLE IF NOT EXISTS course_studio_settings (
  id SERIAL PRIMARY KEY, course_id INTEGER NOT NULL UNIQUE REFERENCES courses(id),
  parent_view JSON NOT NULL DEFAULT '{}', rewards JSON NOT NULL DEFAULT '{}',
  face_dismissed BOOLEAN NOT NULL DEFAULT FALSE, updated_by INTEGER REFERENCES users(id),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_course_studio_settings_course_id ON course_studio_settings(course_id);
ALTER TABLE user_game_stats ADD COLUMN IF NOT EXISTS streak_freeze_month VARCHAR(7);
ALTER TABLE user_game_stats ADD COLUMN IF NOT EXISTS streak_freezes_used INTEGER NOT NULL DEFAULT 0;
