-- WP7 (v2.0 §9): tutor escalations + learner content-error reports. Parity with Alembic 0013.
CREATE TABLE IF NOT EXISTS tutor_escalations (
  id SERIAL PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id),
  student_id INTEGER NOT NULL REFERENCES users(id), instructor_id INTEGER NOT NULL REFERENCES users(id),
  question TEXT NOT NULL, context JSON NOT NULL DEFAULT '{}', status VARCHAR(16) NOT NULL DEFAULT 'open',
  instructor_reply TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), answered_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_tutor_escalations_course_id ON tutor_escalations(course_id);
CREATE INDEX IF NOT EXISTS ix_tutor_escalations_student_id ON tutor_escalations(student_id);
CREATE INDEX IF NOT EXISTS ix_tutor_escalations_instructor_id ON tutor_escalations(instructor_id);
CREATE INDEX IF NOT EXISTS ix_tutor_escalations_status ON tutor_escalations(status);
CREATE TABLE IF NOT EXISTS content_error_reports (
  id SERIAL PRIMARY KEY, reporter_id INTEGER NOT NULL REFERENCES users(id),
  course_id INTEGER NOT NULL REFERENCES courses(id), instructor_id INTEGER NOT NULL REFERENCES users(id),
  kind VARCHAR(20) NOT NULL, ref_id INTEGER, message TEXT NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'open',
  resolution TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_content_error_reports_reporter_id ON content_error_reports(reporter_id);
CREATE INDEX IF NOT EXISTS ix_content_error_reports_course_id ON content_error_reports(course_id);
CREATE INDEX IF NOT EXISTS ix_content_error_reports_instructor_id ON content_error_reports(instructor_id);
CREATE INDEX IF NOT EXISTS ix_content_error_reports_status ON content_error_reports(status);
