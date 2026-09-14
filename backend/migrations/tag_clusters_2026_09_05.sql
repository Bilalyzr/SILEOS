-- WP4 (v2.0 §3): emergent tag taxonomy. Parity with Alembic 0010.
CREATE TABLE IF NOT EXISTS tag_clusters (
  id SERIAL PRIMARY KEY, label VARCHAR(120), member_tags JSON NOT NULL DEFAULT '[]',
  size INTEGER NOT NULL DEFAULT 0, centroid JSON, updated_at TIMESTAMPTZ DEFAULT now());
-- Down: DROP TABLE IF EXISTS tag_clusters;
