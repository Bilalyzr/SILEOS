-- GeoGebra integration (2026-09-04) — parity for ensure_schema/create_all.
-- Applets attach to lessons of FREE courses only (courses.py resolver).
CREATE TABLE IF NOT EXISTS geogebra_applets (
  id          SERIAL PRIMARY KEY,
  owner_id    INTEGER NOT NULL REFERENCES users(id),
  title       VARCHAR(200) NOT NULL,
  app_type    VARCHAR(20) NOT NULL DEFAULT 'graphing',
  material_id VARCHAR(100),
  ggb_base64  TEXT,
  config      JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_geogebra_applets_owner ON geogebra_applets (owner_id);
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS geogebra_applet_id INTEGER;
