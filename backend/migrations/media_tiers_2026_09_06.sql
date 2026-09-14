-- Roadmap item 9: pre-built 3D tiers recorded per model. Parity with Alembic 0019.
ALTER TABLE three_d_models ADD COLUMN IF NOT EXISTS tier_files JSON;
