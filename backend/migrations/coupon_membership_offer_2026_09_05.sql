-- R7 coupons on memberships (Razorpay Offer link). Parity with Alembic 0017.
ALTER TABLE coupons ADD COLUMN IF NOT EXISTS razorpay_offer_id VARCHAR(64);
