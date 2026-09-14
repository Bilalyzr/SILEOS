-- R8 assessment integrity: timed windows + retired questions. Parity with Alembic 0018.
ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS quiz_available_from TIMESTAMPTZ;
ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS quiz_available_until TIMESTAMPTZ;
ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS is_retired BOOLEAN NOT NULL DEFAULT FALSE;
