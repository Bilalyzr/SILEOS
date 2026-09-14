-- Internship requests table for company dashboard v2
-- Companies can request new internships, admins approve/reject
BEGIN;

CREATE TABLE IF NOT EXISTS internship_requests (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    requested_by INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    intern_count INTEGER NOT NULL DEFAULT 1,
    description TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    rejection_reason TEXT NOT NULL DEFAULT '',
    approved_internship_id INTEGER REFERENCES internships(id),
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_internship_requests_company ON internship_requests (company_id);
CREATE INDEX IF NOT EXISTS ix_internship_requests_status ON internship_requests (status);

COMMIT;
