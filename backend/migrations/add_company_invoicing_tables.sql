-- Company invoicing sub-project. Fresh DBs get these from init_db(); run manually
-- against existing Postgres:
--   docker-compose exec postgres psql -U tutor -d tutor_lms -f /path/to/this.sql

CREATE TABLE IF NOT EXISTS company_invoices (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    invoice_number VARCHAR(30) UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    subtotal NUMERIC(12,2) NOT NULL,
    cgst NUMERIC(12,2) NOT NULL DEFAULT 0,
    sgst NUMERIC(12,2) NOT NULL DEFAULT 0,
    igst NUMERIC(12,2) NOT NULL DEFAULT 0,
    total NUMERIC(12,2) NOT NULL,
    tax_note VARCHAR(255) DEFAULT '',
    due_date TIMESTAMPTZ,
    issued_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    paid_via VARCHAR(50) DEFAULT '',
    payment_reference VARCHAR(100) DEFAULT '',
    pdf_path VARCHAR(500) DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_company_invoices_company_id
    ON company_invoices (company_id);

CREATE TABLE IF NOT EXISTS company_invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES company_invoices(id),
    description VARCHAR(255) NOT NULL,
    course_id INTEGER REFERENCES courses(id),
    bundle_id INTEGER REFERENCES bundles(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    line_total NUMERIC(12,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_company_invoice_items_invoice_id
    ON company_invoice_items (invoice_id);

CREATE TABLE IF NOT EXISTS company_seat_pools (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    invoice_id INTEGER NOT NULL REFERENCES company_invoices(id),
    order_id INTEGER REFERENCES orders(id),
    course_id INTEGER REFERENCES courses(id),
    bundle_id INTEGER REFERENCES bundles(id),
    total_seats INTEGER NOT NULL,
    used_seats INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_company_seat_pools_company_id
    ON company_seat_pools (company_id);

CREATE TABLE IF NOT EXISTS company_seat_assignments (
    id SERIAL PRIMARY KEY,
    pool_id INTEGER NOT NULL REFERENCES company_seat_pools(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    assigned_by INTEGER NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_company_seat_assignments_pool_id
    ON company_seat_assignments (pool_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_seat_assignment_pool_user
    ON company_seat_assignments (pool_id, user_id);

CREATE TABLE IF NOT EXISTS invoice_counter (
    fiscal_year VARCHAR(4) PRIMARY KEY,
    last_number INTEGER NOT NULL DEFAULT 0
);

-- Company billing columns
ALTER TABLE companies ADD COLUMN IF NOT EXISTS gstin VARCHAR(20) DEFAULT '';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS legal_name VARCHAR(255) DEFAULT '';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS billing_address TEXT DEFAULT '';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS state_code VARCHAR(2) DEFAULT '';
