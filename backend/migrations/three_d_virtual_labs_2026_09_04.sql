-- Phase 2: 3D models + virtual labs (parity; create_all covers fresh DBs)
CREATE TABLE IF NOT EXISTS three_d_models (
  id              SERIAL PRIMARY KEY,
  owner_id        INTEGER NOT NULL REFERENCES users(id),
  title           VARCHAR(200) NOT NULL,
  file_path       VARCHAR(500) NOT NULL,
  file_size_bytes INTEGER DEFAULT 0,
  format          VARCHAR(10) DEFAULT 'glb',
  created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_three_d_models_owner ON three_d_models (owner_id);
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS three_d_model_id INTEGER;
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS virtual_lab_sim VARCHAR(50);
