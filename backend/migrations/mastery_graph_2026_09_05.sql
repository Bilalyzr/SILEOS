-- WP3 (v2.0 §9.5/§8.3): learner-scoped mastery graph. Parity with Alembic 0009.
CREATE TABLE IF NOT EXISTS concept_links (
  id SERIAL PRIMARY KEY, kind VARCHAR(24) NOT NULL, ref_id VARCHAR(64) NOT NULL, concept VARCHAR(80) NOT NULL,
  course_id INTEGER REFERENCES courses(id), created_by INTEGER REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_concept_link UNIQUE (kind, ref_id, concept));
CREATE INDEX IF NOT EXISTS ix_concept_links_concept ON concept_links (concept);
CREATE INDEX IF NOT EXISTS ix_concept_links_kind_ref ON concept_links (kind, ref_id);
CREATE TABLE IF NOT EXISTS concept_prerequisites (
  id SERIAL PRIMARY KEY, concept VARCHAR(80) NOT NULL, requires VARCHAR(80) NOT NULL,
  created_by INTEGER REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_concept_prereq UNIQUE (concept, requires));
CREATE TABLE IF NOT EXISTS mastery_evidence (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), concept VARCHAR(80) NOT NULL,
  source_kind VARCHAR(24) NOT NULL, source_ref VARCHAR(64) NOT NULL, score_pct DOUBLE PRECISION NOT NULL,
  weight DOUBLE PRECISION NOT NULL DEFAULT 1.0, course_id INTEGER REFERENCES courses(id), detail JSON,
  created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_mastery_evidence_user_concept ON mastery_evidence (user_id, concept);
CREATE TABLE IF NOT EXISTS learner_mastery (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), concept VARCHAR(80) NOT NULL,
  estimate DOUBLE PRECISION NOT NULL DEFAULT 0, confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  evidence_count INTEGER NOT NULL DEFAULT 0, last_evidence_at TIMESTAMPTZ, updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uq_learner_concept UNIQUE (user_id, concept));
CREATE TABLE IF NOT EXISTS course_outcomes (
  id SERIAL PRIMARY KEY, course_id INTEGER NOT NULL UNIQUE REFERENCES courses(id), outcome_text TEXT NOT NULL DEFAULT '',
  target_concepts JSON NOT NULL DEFAULT '[]', updated_by INTEGER REFERENCES users(id), updated_at TIMESTAMPTZ DEFAULT now());
-- Down: DROP TABLE IF EXISTS course_outcomes, learner_mastery, mastery_evidence, concept_prerequisites, concept_links;
