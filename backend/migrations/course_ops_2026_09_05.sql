-- R6 instructor growth tools: templates + co-instructors. Parity with Alembic 0016.
ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_template BOOLEAN NOT NULL DEFAULT FALSE;
CREATE TABLE IF NOT EXISTS course_collaborators (
  id SERIAL PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id), user_id INTEGER NOT NULL REFERENCES users(id),
  role VARCHAR(20) NOT NULL DEFAULT 'co_instructor', added_by INTEGER REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_course_collaborator UNIQUE (course_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_course_collaborators_course_id ON course_collaborators(course_id);
CREATE INDEX IF NOT EXISTS ix_course_collaborators_user_id ON course_collaborators(user_id);
