-- Parity SQL for Alembic 0021; existing LMS schema required.

BEGIN;

CREATE TABLE IF NOT EXISTS learning_goals (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	target_date DATE NOT NULL, 
	daily_minutes INTEGER NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_learning_goal_user_course UNIQUE (user_id, course_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id)
);

CREATE INDEX IF NOT EXISTS ix_learning_goals_course_id ON learning_goals (course_id);

CREATE INDEX IF NOT EXISTS ix_learning_goals_user_id ON learning_goals (user_id);

CREATE TABLE IF NOT EXISTS learning_interventions (
	id SERIAL NOT NULL, 
	goal_id INTEGER NOT NULL, 
	concept VARCHAR(80) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	reason TEXT NOT NULL, 
	evidence JSON NOT NULL, 
	baseline_score FLOAT, 
	latest_score FLOAT, 
	followup_score FLOAT, 
	instructor_note TEXT, 
	reviewed_by INTEGER, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_intervention_goal_concept UNIQUE (goal_id, concept), 
	FOREIGN KEY(goal_id) REFERENCES learning_goals (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_learning_interventions_goal_id ON learning_interventions (goal_id);

CREATE TABLE IF NOT EXISTS learning_plan_tasks (
	id SERIAL NOT NULL, 
	goal_id INTEGER NOT NULL, 
	task_key VARCHAR(120) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	reason TEXT NOT NULL, 
	concept VARCHAR(80), 
	lesson_id INTEGER, 
	intervention_id INTEGER, 
	session_id INTEGER, 
	minutes INTEGER NOT NULL, 
	due_date DATE NOT NULL, 
	not_before DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	outcome JSON, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_plan_task_goal_key UNIQUE (goal_id, task_key), 
	FOREIGN KEY(goal_id) REFERENCES learning_goals (id), 
	FOREIGN KEY(lesson_id) REFERENCES lessons (id), 
	FOREIGN KEY(intervention_id) REFERENCES learning_interventions (id), 
	UNIQUE (session_id), 
	FOREIGN KEY(session_id) REFERENCES adaptive_sessions (id)
);

CREATE INDEX IF NOT EXISTS ix_learning_plan_tasks_due_date ON learning_plan_tasks (due_date);

CREATE INDEX IF NOT EXISTS ix_learning_plan_tasks_goal_id ON learning_plan_tasks (goal_id);

CREATE INDEX IF NOT EXISTS ix_learning_plan_tasks_intervention_id ON learning_plan_tasks (intervention_id);

COMMIT;
