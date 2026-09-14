-- Bundles & paid cohort seats. Fresh DBs get these from init_db();
-- run manually against existing production Postgres.

CREATE TABLE IF NOT EXISTS bundles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    slug VARCHAR(255) NOT NULL UNIQUE,
    bundle_price NUMERIC(10,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bundle_courses (
    id SERIAL PRIMARY KEY,
    bundle_id INTEGER NOT NULL REFERENCES bundles(id),
    course_id INTEGER NOT NULL REFERENCES courses(id)
);
CREATE INDEX IF NOT EXISTS ix_bundle_courses_bundle_id ON bundle_courses (bundle_id);

ALTER TABLE orders ADD COLUMN IF NOT EXISTS bundle_id INTEGER REFERENCES bundles(id);
CREATE INDEX IF NOT EXISTS ix_orders_bundle_id ON orders (bundle_id);
ALTER TABLE cohorts ADD COLUMN IF NOT EXISTS seat_price NUMERIC(10,2);
