-- Migration: Add coupon tables
-- Description: Creates tables for coupon system with discount codes
-- Idempotent: the pipeline's migration ledger was never baselined, so files
-- already applied by hand must also succeed when the pipeline replays them.
BEGIN;

-- Create enum types (CREATE TYPE has no IF NOT EXISTS; catch the duplicate)
DO $$ BEGIN
    CREATE TYPE discount_type AS ENUM ('percentage', 'fixed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
    CREATE TYPE coupon_applicability AS ENUM ('all_courses', 'specific_courses');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Coupons table
CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT DEFAULT '',

    -- Discount details
    discount_type discount_type NOT NULL,
    discount_value DECIMAL(10, 2) NOT NULL,

    -- Applicability
    applicability coupon_applicability NOT NULL DEFAULT 'all_courses',

    -- Usage limits
    usage_limit INTEGER NULL,  -- NULL means unlimited
    usage_count INTEGER DEFAULT 0,
    per_user_limit INTEGER DEFAULT 1,

    -- Minimum purchase
    minimum_purchase_amount DECIMAL(10, 2) DEFAULT 0,

    -- Validity
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE NULL,  -- NULL means no expiry

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for coupons
CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code);
CREATE INDEX IF NOT EXISTS idx_coupons_is_active ON coupons(is_active);
CREATE INDEX IF NOT EXISTS idx_coupons_valid_until ON coupons(valid_until);
CREATE INDEX IF NOT EXISTS idx_coupons_created_by ON coupons(created_by);

-- Coupon course restrictions table (for specific_courses applicability)
CREATE TABLE IF NOT EXISTS coupon_course_restrictions (
    id SERIAL PRIMARY KEY,
    coupon_id INTEGER NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(coupon_id, course_id)
);

-- Create indexes for coupon course restrictions
CREATE INDEX IF NOT EXISTS idx_coupon_course_restrictions_coupon ON coupon_course_restrictions(coupon_id);
CREATE INDEX IF NOT EXISTS idx_coupon_course_restrictions_course ON coupon_course_restrictions(course_id);

-- Coupon usage tracking table
CREATE TABLE IF NOT EXISTS coupon_usage (
    id SERIAL PRIMARY KEY,
    coupon_id INTEGER NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id INTEGER NULL REFERENCES orders(id) ON DELETE SET NULL,

    discount_amount DECIMAL(10, 2) NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for coupon usage
CREATE INDEX IF NOT EXISTS idx_coupon_usage_coupon ON coupon_usage(coupon_id);
CREATE INDEX IF NOT EXISTS idx_coupon_usage_user ON coupon_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_coupon_usage_order ON coupon_usage(order_id);
CREATE INDEX IF NOT EXISTS idx_coupon_usage_used_at ON coupon_usage(used_at);

-- Create trigger to update updated_at timestamp (no IF NOT EXISTS on
-- CREATE TRIGGER; catch the duplicate)
CREATE OR REPLACE FUNCTION update_coupons_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER trigger_update_coupons_updated_at
    BEFORE UPDATE ON coupons
    FOR EACH ROW
    EXECUTE FUNCTION update_coupons_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Insert sample coupons for testing
INSERT INTO coupons (code, description, discount_type, discount_value, applicability, usage_limit, per_user_limit, minimum_purchase_amount, valid_from, valid_until, is_active, created_by)
VALUES
    ('WELCOME10', 'Welcome discount for new users', 'percentage', 10.00, 'all_courses', NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days', TRUE, 1),
    ('SAVE500', 'Save ₹500 on purchase above ₹5000', 'fixed', 500.00, 'all_courses', 100, 1, 5000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '60 days', TRUE, 1),
    ('NEWYEAR50', 'New Year special - 50% off', 'percentage', 50.00, 'all_courses', 50, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '7 days', TRUE, 1)
ON CONFLICT DO NOTHING;

COMMIT;
