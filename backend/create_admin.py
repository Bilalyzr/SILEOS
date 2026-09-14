"""
Create a single admin user in the database
"""

import os

from app.core.database import SessionLocal, engine
from app.models.user import User, UserProfile, Base
from app.core.security import get_password_hash
from datetime import datetime

# Fail closed: require an explicit admin password rather than shipping a known
# default like "Admin@123".
admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    raise SystemExit("ADMIN_PASSWORD env var is required to create the admin user.")

# Create tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.user_email == "admin@sashainfinity.com").first()

    if existing_admin:
        print("Admin user already exists!")
    else:
        # Create admin user
        admin_user = User(
            user_login="admin",
            user_email="admin@sashainfinity.com",
            user_pass=get_password_hash(admin_password),
            user_nicename="admin",
            display_name="System Administrator",
            user_status=1,  # 0 = pending, 1 = active
            role="admin",
            is_active=True,
            user_registered=datetime.utcnow()
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Create admin profile
        admin_profile = UserProfile(
            user_id=admin_user.id,
            first_name="System",
            last_name="Administrator",
            phone="",
            description="System Administrator Account",
            profile_photo="",
            designation="Administrator"
        )

        db.add(admin_profile)
        db.commit()

        print("✓ Admin user created successfully!")
        print(f"  Email: admin@sashainfinity.com")
        print(f"  Password: (set from ADMIN_PASSWORD env var)")
        print(f"  Role: admin")

finally:
    db.close()
