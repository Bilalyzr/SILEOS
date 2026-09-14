-- WP2 (v2.0 §6): 3D match-and-verify tasks + attempts. Parity with Alembic 0008.
CREATE TABLE IF NOT EXISTS three_d_tasks (
  id          SERIAL PRIMARY KEY,
  owner_id    INTEGER NOT NULL REFERENCES users(id),
  model_id    INTEGER NOT NULL REFERENCES three_d_models(id),
  title       VARCHAR(200) NOT NULL,
  task_type   VARCHAR(16) NOT NULL,
  config      JSON NOT NULL,
  concepts    JSON NOT NULL DEFAULT '[]',
  tier_floor  VARCHAR(2) NOT NULL DEFAULT 'T4',
  status      VARCHAR(16) NOT NULL DEFAULT 'draft',
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_three_d_tasks_owner_id ON three_d_tasks (owner_id);
CREATE INDEX IF NOT EXISTS ix_three_d_tasks_model_id ON three_d_tasks (model_id);
CREATE TABLE IF NOT EXISTS three_d_task_attempts (
  id                SERIAL PRIMARY KEY,
  task_id           INTEGER NOT NULL REFERENCES three_d_tasks(id),
  user_id           INTEGER NOT NULL REFERENCES users(id),
  score             INTEGER NOT NULL,
  max_score         INTEGER NOT NULL,
  mode              VARCHAR(2) NOT NULL DEFAULT 'T1',
  answers           JSON NOT NULL DEFAULT '{}',
  evidence          JSON NOT NULL DEFAULT '[]',
  confidence        VARCHAR(16) NOT NULL DEFAULT 'unknown',
  confidence_detail JSON NOT NULL DEFAULT '{}',
  duration_s        INTEGER NOT NULL DEFAULT 0,
  created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_three_d_task_attempts_task_id ON three_d_task_attempts (task_id);
CREATE INDEX IF NOT EXISTS ix_three_d_task_attempts_user_id ON three_d_task_attempts (user_id);
-- Down: DROP TABLE IF EXISTS three_d_task_attempts; DROP TABLE IF EXISTS three_d_tasks;
