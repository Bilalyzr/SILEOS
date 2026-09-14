-- PostgreSQL schema parity for Alembic 0022
BEGIN;

CREATE TABLE IF NOT EXISTS studio_questions (
	id SERIAL NOT NULL, 
	course_id INTEGER NOT NULL, 
	bank_question_id INTEGER NOT NULL, 
	concept VARCHAR(80) NOT NULL, 
	purpose VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	version INTEGER NOT NULL, 
	published_snapshot JSON, 
	history JSON NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id), 
	UNIQUE (bank_question_id), 
	FOREIGN KEY(bank_question_id) REFERENCES bank_questions (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
)

;
CREATE INDEX IF NOT EXISTS ix_studio_questions_concept ON studio_questions (concept);
CREATE INDEX IF NOT EXISTS ix_studio_questions_course_id ON studio_questions (course_id);
COMMIT;
