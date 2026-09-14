-- Company Dashboard v2 — 2026-05-05
-- Adds: company_managers, daily_work_logs, internship_announcements,
--       internship_performance_reviews
-- Modifies: internship_attendance (+hours_worked),
--           internship_vouchers (+reporting_manager_user_id)

BEGIN;

-- Add hours_worked to existing attendance table
ALTER TABLE internship_attendance
    ADD COLUMN IF NOT EXISTS hours_worked NUMERIC(4,2) NOT NULL DEFAULT 0;

-- Add reporting_manager to vouchers table
ALTER TABLE internship_vouchers
    ADD COLUMN IF NOT EXISTS reporting_manager_user_id INTEGER
        REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_vouchers_reporting_manager
    ON internship_vouchers (reporting_manager_user_id);

-- Company managers table (sub-users)
CREATE TABLE IF NOT EXISTS company_managers (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_company_managers_company
    ON company_managers (company_id);

-- Daily work logs (student daily work-done entries)
CREATE TABLE IF NOT EXISTS daily_work_logs (
    id SERIAL PRIMARY KEY,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    internship_id INTEGER NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    attachment_url VARCHAR(500) NOT NULL DEFAULT '',
    review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    reviewed_by INTEGER REFERENCES users(id),
    reviewer_comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_work_log_student_date UNIQUE (student_user_id, log_date)
);
CREATE INDEX IF NOT EXISTS ix_work_logs_internship_date
    ON daily_work_logs (internship_id, log_date);

-- Company announcements to interns
CREATE TABLE IF NOT EXISTS internship_announcements (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    internship_id INTEGER REFERENCES internships(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_announcements_company
    ON internship_announcements (company_id);

-- Performance reviews (end-of-internship)
CREATE TABLE IF NOT EXISTS internship_performance_reviews (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    internship_id INTEGER NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT NOT NULL DEFAULT '',
    hire_recommendation VARCHAR(10) NOT NULL DEFAULT 'maybe',
    submitted_by INTEGER REFERENCES users(id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_review_company_student_internship
        UNIQUE (company_id, student_user_id, internship_id)
);

COMMIT;
