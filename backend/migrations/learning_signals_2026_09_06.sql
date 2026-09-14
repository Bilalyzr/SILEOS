-- Learning-signals engine. Parity with Alembic 0020.
CREATE TABLE IF NOT EXISTS learning_signals (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER REFERENCES courses(id),
  lesson_id INTEGER REFERENCES lessons(id), quiz_id INTEGER, question_id INTEGER, kind VARCHAR(32) NOT NULL,
  position_s INTEGER, segment INTEGER, value DOUBLE PRECISION, meta JSON, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_learning_signals_user_id ON learning_signals(user_id);
CREATE INDEX IF NOT EXISTS ix_learning_signals_course_id ON learning_signals(course_id);
CREATE INDEX IF NOT EXISTS ix_learning_signals_lesson_id ON learning_signals(lesson_id);
CREATE INDEX IF NOT EXISTS ix_learning_signals_quiz_id ON learning_signals(quiz_id);
CREATE INDEX IF NOT EXISTS ix_learning_signals_question_id ON learning_signals(question_id);
CREATE INDEX IF NOT EXISTS ix_learning_signals_kind ON learning_signals(kind);
CREATE INDEX IF NOT EXISTS ix_learning_signals_created_at ON learning_signals(created_at);
CREATE TABLE IF NOT EXISTS lesson_concept_markers (
  id SERIAL PRIMARY KEY, lesson_id INTEGER NOT NULL REFERENCES lessons(id), time_s INTEGER NOT NULL,
  concept VARCHAR(80) NOT NULL, created_by INTEGER REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_lesson_concept_markers_lesson_id ON lesson_concept_markers(lesson_id);
CREATE TABLE IF NOT EXISTS adaptive_sessions (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER NOT NULL REFERENCES courses(id),
  question_ids JSON NOT NULL DEFAULT '[]', plan JSON, answers JSON, results JSON, score INTEGER, max_score INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(), submitted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_adaptive_sessions_user_id ON adaptive_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_adaptive_sessions_course_id ON adaptive_sessions(course_id);
