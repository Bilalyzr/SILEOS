-- Parent/guardian layer (2026-09-05): link table only; parents are users
-- with role='parent'. Digests are computed live, never stored.
CREATE TABLE IF NOT EXISTS parent_students (
  id SERIAL PRIMARY KEY,
  parent_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  linked_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_parent_student UNIQUE (parent_user_id, student_user_id)
);
CREATE INDEX IF NOT EXISTS ix_parent_students_parent ON parent_students (parent_user_id);
