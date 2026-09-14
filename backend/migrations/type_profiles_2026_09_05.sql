-- Type-driven architecture v2.0 (Sasha_LMS_Architecture_v2.pdf §2.3, §5.3)
-- The type profile is DATA, not code: a new type becomes a row, not a release.
CREATE TABLE IF NOT EXISTS type_profiles (
  type                          VARCHAR(20) PRIMARY KEY,
  label                         VARCHAR(100) NOT NULL,
  default_enabled_tools         JSONB NOT NULL,
  default_assessment_weights    JSONB NOT NULL,
  learner_path_template         JSONB DEFAULT '{}'
);

INSERT INTO type_profiles (type, label, default_enabled_tools, default_assessment_weights)
VALUES
  ('meiporul', 'Meiporul (AR/VR)',
   '["video","quiz","three_d_models","geogebra","h5p","virtual_labs"]',
   '{"quizzes":25,"three_d_tasks":50,"games_h5p":10,"assignments":15}'),
  ('seyappaduporul', 'Seyappaduporul (School)',
   '["video","quiz","games","h5p","live_classes","learning_paths","rewards","virtual_labs","geogebra"]',
   '{"quizzes":30,"three_d_tasks":10,"games_h5p":25,"assignments":15,"live_participation":20}'),
  ('utporul', 'Utporul (Skill)',
   '["video","quiz","games","h5p","live_classes","learning_paths","rewards","geogebra","three_d_models","virtual_labs"]',
   '{"quizzes":40,"three_d_tasks":15,"games_h5p":15,"assignments":20,"live_participation":10}')
ON CONFLICT (type) DO NOTHING;

-- "Add more tools" escape hatch: courses may extend beyond their type's
-- defaults (defaults, not walls — v2.0 §1 recommendation).
ALTER TABLE courses ADD COLUMN IF NOT EXISTS enabled_tools JSONB;
