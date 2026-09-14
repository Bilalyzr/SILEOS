#!/usr/bin/env python3
"""
Secure Admin Seeding Script for SashaInfinity LMS
Creates a secure admin user with proper password hashing and verification
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.core.config import get_settings

# Import models directly to avoid circular dependencies
from app.models.user import User, UserProfile

settings = get_settings()

def create_admin_user():
    """Create a secure admin user"""

    # Admin credentials from environment variables.
    admin_email = os.getenv("ADMIN_EMAIL", "admin@sashainfinity.com")
    # Fail closed: never fall back to a hardcoded password (it would ship a
    # known admin credential). ADMIN_PASSWORD must be provided explicitly.
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise SystemExit("ADMIN_PASSWORD env var is required to create the admin user.")
    admin_username = os.getenv("ADMIN_USERNAME", "sashainfinity_admin")
    admin_first_name = os.getenv("ADMIN_FIRST_NAME", "SashaInfinity")
    admin_last_name = os.getenv("ADMIN_LAST_NAME", "Administrator")

    print("🔐 Creating secure admin user for SashaInfinity LMS...")
    print(f"   Email: {admin_email}")
    print(f"   Username: {admin_username}")

    # Create database session
    db: Session = SessionLocal()

    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(
            (User.user_email == admin_email) | (User.user_login == admin_username)
        ).first()

        if existing_admin:
            print("⚠️  Admin user already exists!")
            print(f"   ID: {existing_admin.id}")
            print(f"   Email: {existing_admin.user_email}")
            print(f"   Role: {existing_admin.role}")
            print(f"   Status: {'Active' if existing_admin.is_active else 'Inactive'}")
            print(f"   Verified: {'Yes' if existing_admin.is_verified else 'No'}")

            # Update existing admin if needed
            if existing_admin.role != "admin":
                existing_admin.role = "admin"
                print("✅ Updated user role to 'admin'")

            if not existing_admin.is_verified:
                existing_admin.is_verified = True
                print("✅ Verified admin account")

            if not existing_admin.is_active:
                existing_admin.is_active = True
                print("✅ Activated admin account")

            db.commit()
            return existing_admin

        # Hash the password securely
        print("🔒 Hashing admin password...")
        hashed_password = get_password_hash(admin_password)

        # Create admin user
        admin_user = User(
            user_login=admin_username,
            user_pass=hashed_password,
            user_nicename=admin_username.lower(),
            user_email=admin_email,
            user_url="",
            user_activation_key="",
            user_status=0,
            display_name=f"{admin_first_name} {admin_last_name}",
            role="admin",
            is_active=True,
            is_verified=True,  # Auto-verify admin account
            profile_completed=True,
            last_login=datetime.utcnow()
        )

        db.add(admin_user)
        db.flush()  # Get the user ID

        # Create admin profile
        admin_profile = UserProfile(
            user_id=admin_user.id,
            first_name=admin_first_name,
            last_name=admin_last_name,
            description="System Administrator",
            phone="+91 8438740893",
            designation="System Administrator",
            address="Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu 636004",
            city="Salem",
            state="Tamil Nadu",
            country="India",
            postal_code="636004",
            profile_photo="",
            cover_photo="",
            facebook="https://www.instagram.com/sashainfinityedu?igsh=cmVycTFseHRjYmw2",
            linkedin="https://www.linkedin.com/company/sashainfinity/",
            website="https://sashainfinity.com",
            show_email=False,
            receive_notifications=True
        )

        db.add(admin_profile)
        db.commit()

        print("✅ Admin user created successfully!")
        print(f"   User ID: {admin_user.id}")
        print(f"   Email: {admin_user.user_email}")
        print(f"   Username: {admin_user.user_login}")
        print(f"   Role: {admin_user.role}")
        print(f"   Verified: {admin_user.is_verified}")
        print(f"   Active: {admin_user.is_active}")
        print(f"   Created: {admin_user.created_at}")

        return admin_user

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables_if_not_exist():
    """Create database tables if they don't exist"""
    print("🗄️  Checking database connection...")
    try:
        # Just test database connection - tables should already exist from main app
        from sqlalchemy import text
        db: Session = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        raise

def verify_admin_access():
    """Verify admin can access the system"""
    print("\n🔍 Verifying admin access...")

    db: Session = SessionLocal()

    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if admin:
            print(f"✅ Admin user found: {admin.user_email}")
            print(f"   ID: {admin.id}")
            print(f"   Active: {admin.is_active}")
            print(f"   Verified: {admin.is_verified}")
            return True
        else:
            print("❌ No admin user found in database")
            return False
    except Exception as e:
        print(f"❌ Error verifying admin: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """Main seeding function"""
    print("🚀 Starting SashaInfinity LMS Admin Seeding")
    print("=" * 50)

    try:
        # Create tables if needed
        create_tables_if_not_exist()

        # Create admin user
        admin = create_admin_user()

        # Verify admin access
        if verify_admin_access():
            print("\n🎉 Admin seeding completed successfully!")
            print("\n📋 Login Details:")
            print(f"   Email: {admin.user_email}")
            print(f"   Username: {admin.user_login}")
            print(f"   Password: [Set via ADMIN_PASSWORD environment variable]")
            print(f"   Login URL: {settings.FRONTEND_URL}/login")
            print("\n⚠️  IMPORTANT: Keep the admin password secure and change it regularly!")
        else:
            print("❌ Admin verification failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Admin seeding failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()