-- Content libraries (2026-09-05): admin-curated virtual lab catalog, native lab
-- results, and the shared 3D asset library flag. Parity with Alembic revision
-- 0007_content_libraries (create_all covers fresh DBs; run this on Postgres
-- installs that are not on Alembic).
CREATE TABLE IF NOT EXISTS virtual_lab_catalog (
  id              SERIAL PRIMARY KEY,
  slug            VARCHAR(50) NOT NULL UNIQUE,
  title           VARCHAR(200) NOT NULL,
  subject         VARCHAR(50) NOT NULL DEFAULT 'general',
  description     TEXT,
  provider        VARCHAR(16) NOT NULL DEFAULT 'embed',
  embed_url       VARCHAR(1000),
  native_template VARCHAR(32),
  config          JSON,
  attribution     VARCHAR(300),
  thumbnail_url   VARCHAR(1000),
  is_published    BOOLEAN NOT NULL DEFAULT TRUE,
  created_by      INTEGER REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_virtual_lab_catalog_slug ON virtual_lab_catalog (slug);

CREATE TABLE IF NOT EXISTS virtual_lab_results (
  id          SERIAL PRIMARY KEY,
  lab_slug    VARCHAR(50) NOT NULL,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  score       INTEGER NOT NULL,
  max_score   INTEGER NOT NULL,
  duration_s  INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_virtual_lab_results_lab_slug ON virtual_lab_results (lab_slug);
CREATE INDEX IF NOT EXISTS ix_virtual_lab_results_user_id ON virtual_lab_results (user_id);

ALTER TABLE three_d_models ADD COLUMN IF NOT EXISTS is_library BOOLEAN NOT NULL DEFAULT FALSE;

-- Down path:
-- ALTER TABLE three_d_models DROP COLUMN IF EXISTS is_library;
-- DROP TABLE IF EXISTS virtual_lab_results;
-- DROP TABLE IF EXISTS virtual_lab_catalog;
