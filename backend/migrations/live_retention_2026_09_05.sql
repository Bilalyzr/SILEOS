-- WP5 (v2.0 §7): live-class classification, retention, permanent reports, deletion audit. Parity with Alembic 0011.
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS purpose VARCHAR(24);
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS mode VARCHAR(24);
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS audience VARCHAR(16);
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_policy VARCHAR(12);
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ;
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_deleted_at TIMESTAMPTZ;
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_deleted_by INTEGER REFERENCES users(id);
ALTER TABLE live_classes ADD COLUMN IF NOT EXISTS recording_delete_reason VARCHAR(300);
CREATE TABLE IF NOT EXISTS class_reports (
  id SERIAL PRIMARY KEY, class_id INTEGER NOT NULL UNIQUE REFERENCES live_classes(id),
  course_id INTEGER NOT NULL REFERENCES courses(id), instructor_id INTEGER NOT NULL REFERENCES users(id),
  title VARCHAR(200) NOT NULL, purpose VARCHAR(24), scheduled_start TIMESTAMPTZ, started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ,
  duration_s INTEGER NOT NULL DEFAULT 0, attendance JSON NOT NULL DEFAULT '[]', event_log JSON NOT NULL DEFAULT '[]',
  poll_results JSON NOT NULL DEFAULT '[]', engagement JSON NOT NULL DEFAULT '{}', instructor_notes TEXT NOT NULL DEFAULT '',
  transcript TEXT, ai_topics JSON, processing_status VARCHAR(16) NOT NULL DEFAULT 'pending',
  shared_with_guardians BOOLEAN NOT NULL DEFAULT FALSE, generated_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_class_reports_course_id ON class_reports (course_id);
CREATE TABLE IF NOT EXISTS recording_audit (
  id SERIAL PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES live_classes(id), actor_id INTEGER REFERENCES users(id),
  action VARCHAR(24) NOT NULL, reason VARCHAR(300), detail JSON, created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_recording_audit_class_id ON recording_audit (class_id);
-- Down: DROP TABLE IF EXISTS recording_audit, class_reports; ALTER TABLE live_classes DROP COLUMN ... (8 columns)
