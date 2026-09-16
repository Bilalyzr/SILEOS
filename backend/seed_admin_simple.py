#!/usr/bin/env python3
"""
Simple Admin Seeding Script for SashaInfinity LMS
Uses raw SQL to avoid model relationship issues
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
import hashlib

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()

def create_admin_user_sql():
    """Create admin user using raw SQL to avoid relationship issues"""

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
        check_sql = text("""
        SELECT id, user_email, user_login, role, is_active, is_verified
        FROM users
        WHERE user_email = :email OR user_login = :username
        """)

        result = db.execute(check_sql, {"email": admin_email, "username": admin_username}).fetchone()

        if result:
            print("⚠️  Admin user already exists!")
            print(f"   ID: {result[0]}")
            print(f"   Email: {result[1]}")
            print(f"   Username: {result[2]}")
            print(f"   Role: {result[3]}")
            print(f"   Status: {'Active' if result[4] else 'Inactive'}")
            print(f"   Verified: {'Yes' if result[5] else 'No'}")

            # Update existing admin if needed
            update_sql = text("""
            UPDATE users
            SET role = 'admin', is_verified = TRUE, is_active = TRUE
            WHERE id = :user_id
            """)
            db.execute(update_sql, {"user_id": result[0]})
            db.commit()

            print("✅ Updated user to 'admin' role with verification")
            return result[0]

        # Hash the password securely
        print("🔒 Hashing admin password...")
        hashed_password = get_password_hash(admin_password)

        # Get current timestamp
        current_time = datetime.utcnow()

        # Insert admin user
        insert_user_sql = text("""
        INSERT INTO users (
            user_login, user_pass, user_nicename, user_email, user_url,
            user_activation_key, user_status, display_name, role,
            is_active, is_verified, profile_completed, last_login,
            user_registered, created_at, updated_at
        ) VALUES (
            :user_login, :user_pass, :user_nicename, :user_email, :user_url,
            :user_activation_key, :user_status, :display_name, :role,
            :is_active, :is_verified, :profile_completed, :last_login,
            :user_registered, :created_at, :updated_at
        ) RETURNING id
        """)

        user_params = {
            "user_login": admin_username,
            "user_pass": hashed_password,
            "user_nicename": admin_username.lower(),
            "user_email": admin_email,
            "user_url": "",
            "user_activation_key": "",
            "user_status": 0,
            "display_name": f"{admin_first_name} {admin_last_name}",
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "profile_completed": True,
            "last_login": current_time,
            "user_registered": current_time,
            "created_at": current_time,
            "updated_at": current_time
        }

        result = db.execute(insert_user_sql, user_params).fetchone()
        user_id = result[0]

        print(f"✅ Created admin user with ID: {user_id}")

        # Insert admin profile
        insert_profile_sql = text("""
        INSERT INTO user_profiles (
            user_id, first_name, last_name, description, phone, designation,
            address, city, state, country, postal_code, profile_photo,
            cover_photo, facebook, linkedin, website, show_email,
            receive_notifications, created_at, updated_at
        ) VALUES (
            :user_id, :first_name, :last_name, :description, :phone, :designation,
            :address, :city, :state, :country, :postal_code, :profile_photo,
            :cover_photo, :facebook, :linkedin, :website, :show_email,
            :receive_notifications, :created_at, :updated_at
        )
        """)

        profile_params = {
            "user_id": user_id,
            "first_name": admin_first_name,
            "last_name": admin_last_name,
            "description": "System Administrator",
            "phone": "+91 8438740893",
            "designation": "System Administrator",
            "address": "Ward 1, Uthayapuri Colony, Narasothipatti, Salem, Tamil Nadu 636004",
            "city": "Salem",
            "state": "Tamil Nadu",
            "country": "India",
            "postal_code": "636004",
            "profile_photo": "",
            "cover_photo": "",
            "facebook": "https://www.instagram.com/sashainfinityedu?igsh=cmVycTFseHRjYmw2",
            "linkedin": "https://www.linkedin.com/company/sashainfinity/",
            "website": "https://sashainfinity.com",
            "show_email": False,
            "receive_notifications": True,
            "created_at": current_time,
            "updated_at": current_time
        }

        db.execute(insert_profile_sql, profile_params)
        db.commit()

        print("✅ Admin user and profile created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {admin_email}")
        print(f"   Username: {admin_username}")
        print(f"   Role: admin")
        print(f"   Verified: True")
        print(f"   Active: True")

        return user_id

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_admin_access():
    """Verify admin can access the system"""
    print("\n🔍 Verifying admin access...")

    db: Session = SessionLocal()

    try:
        check_sql = text("""
        SELECT id, user_email, user_login, role, is_active, is_verified
        FROM users
        WHERE role = 'admin'
        LIMIT 1
        """)

        result = db.execute(check_sql).fetchone()

        if result:
            print(f"✅ Admin user found: {result[1]}")
            print(f"   ID: {result[0]}")
            print(f"   Email: {result[1]}")
            print(f"   Username: {result[2]}")
            print(f"   Role: {result[3]}")
            print(f"   Active: {result[4]}")
            print(f"   Verified: {result[5]}")
            return True
        else:
            print("❌ No admin user found in database")
            return False
    except Exception as e:
        print(f"❌ Error verifying admin: {str(e)}")
        return False
    finally:
        db.close()

def test_database_connection():
    """Test database connection"""
    print("🗄️  Testing database connection...")
    try:
        db: Session = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        db.close()
        print("✅ Database connection verified")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def main():
    """Main seeding function"""
    print("🚀 Starting SashaInfinity LMS Admin Seeding (Simple Version)")
    print("=" * 55)

    try:
        # Test database connection
        if not test_database_connection():
            print("❌ Cannot proceed without database connection")
            sys.exit(1)

        # Create admin user
        admin_id = create_admin_user_sql()

        # Verify admin access
        if verify_admin_access():
            print("\n🎉 Admin seeding completed successfully!")
            print("\n📋 Login Details:")
            print(f"   Email: {os.getenv('ADMIN_EMAIL', 'admin@sashainfinity.com')}")
            print(f"   Username: {os.getenv('ADMIN_USERNAME', 'sashainfinity_admin')}")
            print(f"   Password: [Set via ADMIN_PASSWORD environment variable]")
            print(f"   Login URL: {settings.FRONTEND_URL}/login")
            print("\n⚠️  IMPORTANT: Keep the admin password secure and change it regularly!")
            print("\n💡 Next Steps:")
            print("   1. Test admin login at the URL above")
            print("   2. Update the admin password after first login")
            print("   3. Configure admin permissions and settings")
        else:
            print("❌ Admin verification failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Admin seeding failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()