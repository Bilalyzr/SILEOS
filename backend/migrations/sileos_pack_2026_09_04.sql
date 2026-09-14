-- SILEOS feature pack (docs/SILEOS_FEATURES.md, 2026-09-04)
-- Idempotent parity for the SQLAlchemy models in app/models/sileos_pack.py.
-- On boot, init_db() -> Base.metadata.create_all creates these too; this
-- file exists so an EXISTING live DB can be brought forward without a
-- restart, matching the house migration convention
-- (apply with: psql $DATABASE_URL -f migrations/sileos_pack_2026_09_04.sql)

CREATE TABLE IF NOT EXISTS question_banks (
  id            SERIAL PRIMARY KEY,
  instructor_id INTEGER NOT NULL REFERENCES users(id),
  title         VARCHAR(200) NOT NULL,
  description   TEXT DEFAULT '',
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_question_banks_instructor ON question_banks (instructor_id);

CREATE TABLE IF NOT EXISTS bank_questions (
  id                      SERIAL PRIMARY KEY,
  bank_id                 INTEGER NOT NULL REFERENCES question_banks(id) ON DELETE CASCADE,
  question_title          TEXT NOT NULL,
  question_type           VARCHAR(50) NOT NULL,
  question_mark           DOUBLE PRECISION DEFAULT 1.0,
  options                 JSONB DEFAULT '[]',
  correct_answer          JSONB,
  answer_explanation      TEXT DEFAULT '',
  difficulty              VARCHAR(16) DEFAULT 'medium',
  tags                    JSONB DEFAULT '[]',
  source_quiz_question_id INTEGER,
  created_at              TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_bank_questions_bank ON bank_questions (bank_id);

CREATE TABLE IF NOT EXISTS course_prerequisites (
  id                      SERIAL PRIMARY KEY,
  course_id               INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  requires_course_id      INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  min_progress_percentage INTEGER DEFAULT 100,
  created_at              TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_course_prereq_pair UNIQUE (course_id, requires_course_id)
);
CREATE INDEX IF NOT EXISTS ix_course_prerequisites_course ON course_prerequisites (course_id);

CREATE TABLE IF NOT EXISTS learning_paths (
  id          SERIAL PRIMARY KEY,
  owner_id    INTEGER NOT NULL REFERENCES users(id),
  title       VARCHAR(200) NOT NULL,
  description TEXT DEFAULT '',
  course_ids  JSONB DEFAULT '[]',
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_learning_paths_owner ON learning_paths (owner_id);

CREATE TABLE IF NOT EXISTS xapi_statements (
  id            SERIAL PRIMARY KEY,
  actor_user_id INTEGER NOT NULL REFERENCES users(id),
  verb          VARCHAR(64) NOT NULL,
  object_type   VARCHAR(32) NOT NULL,
  object_id     VARCHAR(64) DEFAULT '',
  object_ref    VARCHAR(500) DEFAULT '',
  result        JSONB DEFAULT '{}',
  context       JSONB DEFAULT '{}',
  stored_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_xapi_actor_time ON xapi_statements (actor_user_id, stored_at);
CREATE INDEX IF NOT EXISTS ix_xapi_verb ON xapi_statements (verb);

CREATE TABLE IF NOT EXISTS ai_jobs (
  id           SERIAL PRIMARY KEY,
  created_by   INTEGER NOT NULL REFERENCES users(id),
  job_type     VARCHAR(50) NOT NULL,
  status       VARCHAR(20) DEFAULT 'pending',
  model        VARCHAR(100) DEFAULT '',
  input_json   JSONB DEFAULT '{}',
  output_json  JSONB DEFAULT '{}',
  error        TEXT DEFAULT '',
  created_at   TIMESTAMPTZ DEFAULT now(),
  finished_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_ai_jobs_created_by ON ai_jobs (created_by);

CREATE TABLE IF NOT EXISTS student_risk_flags (
  id             SERIAL PRIMARY KEY,
  course_id      INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  risk_score     INTEGER DEFAULT 0,
  severity       VARCHAR(16) DEFAULT 'low',
  reasons        JSONB DEFAULT '[]',
  computed_at    TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_risk_course_student UNIQUE (course_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_student_risk_flags_course ON student_risk_flags (course_id);
