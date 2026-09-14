-- PostgreSQL parity for Alembic revision 0023. Prefer alembic upgrade head.

CREATE TABLE IF NOT EXISTS recording_lessons (
	id SERIAL NOT NULL, 
	class_id INTEGER NOT NULL, 
	source_path TEXT NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	language VARCHAR(12) NOT NULL, 
	version INTEGER NOT NULL, 
	attempts INTEGER NOT NULL, 
	error VARCHAR(500), 
	title VARCHAR(200) NOT NULL, 
	notes TEXT NOT NULL, 
	segments JSON NOT NULL, 
	chapters JSON NOT NULL, 
	concepts JSON NOT NULL, 
	question_ids JSON NOT NULL, 
	lesson_id INTEGER, 
	reviewed_by INTEGER, 
	started_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (class_id), 
	FOREIGN KEY(class_id) REFERENCES live_classes (id), 
	UNIQUE (lesson_id), 
	FOREIGN KEY(lesson_id) REFERENCES lessons (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
)

;
CREATE INDEX IF NOT EXISTS ix_recording_lessons_status ON recording_lessons (status);
