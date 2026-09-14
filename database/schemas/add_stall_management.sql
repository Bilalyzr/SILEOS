-- Migration: Add stall management tables (coupons and sizes)
-- Run this against the database to add the new tables and columns

-- Create discount_type enum for coupons
DO $$ BEGIN
    CREATE TYPE discount_type AS ENUM ('fixed', 'percentage');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create stall_sizes table
CREATE TABLE stall_sizes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    price_multiplier NUMERIC(5, 2) NOT NULL DEFAULT 1.00,
    max_quantity INTEGER NOT NULL DEFAULT 10,
    available_quantity INTEGER NOT NULL DEFAULT 10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create stall_sizes index
CREATE INDEX idx_stall_sizes_slug ON stall_sizes(slug);
CREATE INDEX idx_stall_sizes_active ON stall_sizes(is_active);

-- Create stall_coupons table
CREATE TABLE stall_coupons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_amount NUMERIC(10, 2) NOT NULL,
    discount_type discount_type NOT NULL DEFAULT 'fixed',
    max_uses INTEGER,
    used_count INTEGER NOT NULL DEFAULT 0,
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_until TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create stall_coupons index
CREATE INDEX idx_stall_coupons_code ON stall_coupons(code);
CREATE INDEX idx_stall_coupons_active ON stall_coupons(is_active);

-- Add columns to stall_registrations table for stall size and coupon references
ALTER TABLE stall_registrations
ADD COLUMN IF NOT EXISTS stall_size_id INTEGER REFERENCES stall_sizes(id);

ALTER TABLE stall_registrations
ADD COLUMN IF NOT EXISTS coupon_id INTEGER REFERENCES stall_coupons(id);

-- Create indexes for new foreign keys
CREATE INDEX IF NOT EXISTS idx_stall_registrations_stall_size ON stall_registrations(stall_size_id);
CREATE INDEX IF NOT EXISTS idx_stall_registrations_coupon ON stall_registrations(coupon_id);

-- Insert default stall sizes
INSERT INTO stall_sizes (name, slug, description, price_multiplier, max_quantity, available_quantity, is_active, sort_order)
VALUES
    ('Standard Stall', 'standard', 'Standard 10x10 stall with basic amenities', 1.0, 10, 10, TRUE, 1),
    ('Premium Stall', 'premium', 'Premium 12x12 stall with corner location and extra visibility', 1.5, 5, 5, TRUE, 2),
    ('Premium Plus Stall', 'premium-plus', 'Large 15x15 stall with premium location and maximum visibility', 2.0, 3, 3, TRUE, 3)
ON CONFLICT (slug) DO NOTHING;

-- Insert default coupon
INSERT INTO stall_coupons (code, discount_amount, discount_type, max_uses, is_active)
VALUES ('SONA_STU_26', 1000.00, 'fixed', NULL, TRUE)
ON CONFLICT (code) DO UPDATE SET
    discount_amount = EXCLUDED.discount_amount,
    discount_type = EXCLUDED.discount_type,
    is_active = EXCLUDED.is_active;

COMMENT ON TABLE stall_sizes IS 'Stall sizes/tiers with different pricing';
COMMENT ON TABLE stall_coupons IS 'Discount coupons for stall registrations';
