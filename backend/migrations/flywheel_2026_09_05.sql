-- WP8 (v2.0 §10): peer "teach it back" v1. Parity with Alembic 0014.
CREATE TABLE IF NOT EXISTS teach_backs (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
  course_id INTEGER REFERENCES courses(id), concept VARCHAR(80) NOT NULL, text TEXT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'visible', helpful_count INTEGER NOT NULL DEFAULT 0,
  not_helpful_count INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_teach_backs_user_id ON teach_backs(user_id);
CREATE INDEX IF NOT EXISTS ix_teach_backs_course_id ON teach_backs(course_id);
CREATE INDEX IF NOT EXISTS ix_teach_backs_concept ON teach_backs(concept);
CREATE TABLE IF NOT EXISTS teach_back_ratings (
  id SERIAL PRIMARY KEY, teach_back_id INTEGER NOT NULL REFERENCES teach_backs(id) ON DELETE CASCADE,
  rater_id INTEGER NOT NULL REFERENCES users(id), helpful BOOLEAN NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_teach_back_rating UNIQUE (teach_back_id, rater_id)
);
CREATE INDEX IF NOT EXISTS ix_teach_back_ratings_teach_back_id ON teach_back_ratings(teach_back_id);
CREATE INDEX IF NOT EXISTS ix_teach_back_ratings_rater_id ON teach_back_ratings(rater_id);
