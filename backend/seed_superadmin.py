#!/usr/bin/env python3
"""
SuperAdmin seeding script for SashaInfinity LMS.

A SuperAdmin sits *above* `admin`: it inherits every admin endpoint (via
`AuthService.require_admin` accepting `("admin", "superadmin")`) and gains
the superadmin-exclusive monitoring + impersonate-anyone endpoints in
`routers/superadmin.py`.

This script is a thin, role-overriding sibling of `seed_admin_simple.py`:
it reuses the same raw-SQL INSERT shape and the same ADMIN_PASSWORD-style
env contract, but writes `role='superadmin'`.

2FA is MANDATORY for superadmin (enforced at login in routers/auth.py).
Because TOTP enrolment is an interactive, time-based ceremony, this script
does NOT silently mint a TOTP secret — instead it prints a one-time
enrolment URL the operator must scan with an authenticator app, and refuses
to mark the account `totp_enabled=True` until a code has been verified.

Environment variables
---------------------
SUPERADMIN_EMAIL     (default: superadmin@sashainfinity.com)
SUPERADMIN_USERNAME  (default: sashainfinity_superadmin)
SUPERADMIN_PASSWORD  REQUIRED — never hardcoded.
SUPERADMIN_FIRST_NAME / SUPERADMIN_LAST_NAME  (display name parts)
"""

import asyncio
import base64
import hashlib
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()


def _totp_provisioning_url(secret: str, email: str) -> str:
    """Build an otpauth:// URL + a fallback manual-entry hint."""
    issuer = "SashaInfinity"
    label = f"{issuer}:{email}"
    # otpauth URIs are not percent-encoded by spec for the label; keep it simple.
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def _generate_totp_secret() -> str:
    """A random base32 20-byte secret, same shape as core/totp uses."""
    import secrets

    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def create_superadmin_user_sql():
    superadmin_email = os.getenv("SUPERADMIN_EMAIL", "superadmin@sashainfinity.com")
    superadmin_password = os.getenv("SUPERADMIN_PASSWORD")
    if not superadmin_password:
        raise SystemExit(
            "SUPERADMIN_PASSWORD env var is required to create the superadmin user."
        )
    superadmin_username = os.getenv("SUPERADMIN_USERNAME", "sashainfinity_superadmin")
    first_name = os.getenv("SUPERADMIN_FIRST_NAME", "SashaInfinity")
    last_name = os.getenv("SUPERADMIN_LAST_NAME", "SuperAdmin")

    print("🔐 Creating SUPERADMIN user for SashaInfinity LMS...")
    print(f"   Email: {superadmin_email}")
    print(f"   Username: {superadmin_username}")

    db: Session = SessionLocal()
    try:
        # Idempotency: if a superadmin already exists, surface it and stop.
        check_sql = text(
            """
            SELECT id, user_email, user_login, role, totp_enabled
            FROM users
            WHERE role = 'superadmin'
            """
        )
        existing = db.execute(check_sql).fetchone()
        if existing:
            print("⚠️  A superadmin user already exists — not creating another.")
            print(f"   ID: {existing[0]}  email: {existing[1]}  login: {existing[2]}")
            print(f"   totp_enabled: {existing[4]}")
            return existing[0]

        # Also bail if the chosen email/login collides with an existing account
        # of a different role — we never silently re-role another user up.
        collision_sql = text(
            """
            SELECT id, role FROM users
            WHERE user_email = :email OR user_login = :username
            """
        )
        collision = db.execute(
            collision_sql, {"email": superadmin_email, "username": superadmin_username}
        ).fetchone()
        if collision:
            raise SystemExit(
                f"Refusing to create superadmin: email/username already in use by "
                f"user_id={collision[0]} (role={collision[1]})."
            )

        hashed_password = get_password_hash(superadmin_password)
        totp_secret = _generate_totp_secret()
        current_time = datetime.utcnow()

        insert_user_sql = text(
            """
            INSERT INTO users (
                user_login, user_pass, user_nicename, user_email, user_url,
                user_activation_key, user_status, display_name, role,
                is_active, is_verified, profile_completed, last_login,
                totp_secret, totp_enabled,
                user_registered, created_at, updated_at
            ) VALUES (
                :user_login, :user_pass, :user_nicename, :user_email, :user_url,
                :user_activation_key, :user_status, :display_name, :role,
                :is_active, :is_verified, :profile_completed, :last_login,
                :totp_secret, :totp_enabled,
                :user_registered, :created_at, :updated_at
            ) RETURNING id
            """
        )

        user_id = db.execute(
            insert_user_sql,
            {
                "user_login": superadmin_username,
                "user_pass": hashed_password,
                "user_nicename": superadmin_username.lower(),
                "user_email": superadmin_email,
                "user_url": "",
                "user_activation_key": "",
                "user_status": 0,
                "display_name": f"{first_name} {last_name}",
                "role": "superadmin",
                "is_active": True,
                "is_verified": True,
                "profile_completed": True,
                "last_login": current_time,
                # TOTP secret is staged here, but totp_enabled stays False
                # until the operator verifies a code via the standard
                # 2FA-enrolment endpoints — login() hard-refuses superadmins
                # without totp_enabled.
                "totp_secret": totp_secret,
                "totp_enabled": False,
                "user_registered": current_time,
                "created_at": current_time,
                "updated_at": current_time,
            },
        ).fetchone()[0]

        db.commit()
        print(f"✅ Created superadmin user with ID: {user_id}")
        print("\n" + "=" * 60)
        print("🔒 2FA ENROLMENT (REQUIRED before this account can log in)")
        print("=" * 60)
        print("1. Have the superadmin log in once with email+password.")
        print("2. The login will return the standard TOTP enrolment flow;")
        print("   scan the QR / enter the secret in an authenticator app.")
        print("3. Verify a 6-digit code to flip totp_enabled=True.")
        print("\n   Manual secret (base32):")
        print(f"   {totp_secret}")
        print("\n   Provisioning URL:")
        print(f"   {_totp_provisioning_url(totp_secret, superadmin_email)}")
        print("=" * 60)
        return user_id
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating superadmin user: {e}")
        raise
    finally:
        db.close()


def test_database_connection():
    print("🗄️  Testing database connection...")
    try:
        db: Session = SessionLocal()
        db.execute(text("SELECT 1")).fetchone()
        db.close()
        print("✅ Database connection verified")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    print("🚀 SashaInfinity LMS SuperAdmin Seeding")
    print("=" * 50)
    if not test_database_connection():
        sys.exit(1)
    try:
        uid = create_superadmin_user_sql()
        print(f"\n🎉 SuperAdmin seeding complete (user_id={uid}).")
        print("\n⚠️  Finish 2FA enrolment before relying on this account.")
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ SuperAdmin seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
