"""Create (or promote) a Campus platform administrator.

Campus has its own administrators, separate from the LMS admin/superadmin.
They sign in at /campus/login and can support every institution, review plan
requests and recover billing. LMS admin/superadmin have no Campus access.

Usage (inside the backend container, secrets via environment, never argv):
  CAMPUS_ADMIN_EMAIL=ops@example.com CAMPUS_ADMIN_PASSWORD='...' \
    python scripts/create_campus_admin.py
An existing account with that email is switched to the campus_admin role.
"""
import os
import sys

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User

email = os.environ.get("CAMPUS_ADMIN_EMAIL", "").strip().lower()
password = os.environ.get("CAMPUS_ADMIN_PASSWORD", "")
if not email or (len(password) < 12 and not os.environ.get("CAMPUS_ADMIN_KEEP_PASSWORD")):
    sys.exit("Set CAMPUS_ADMIN_EMAIL and a CAMPUS_ADMIN_PASSWORD of 12+ characters.")
db = SessionLocal()
user = db.query(User).filter(User.user_email == email).first()
if user:
    if user.role in ("admin", "superadmin"):
        sys.exit("Refusing to convert an LMS administrator. Use a separate account.")
    user.role = "campus_admin"
    if password:
        user.user_pass = get_password_hash(password)
    action = "promoted"
else:
    user = User(
        user_login=email.split("@")[0][:60], user_pass=get_password_hash(password),
        user_nicename="campus-admin", user_email=email, display_name="Campus administrator",
        role="campus_admin", is_active=True, is_verified=True,
    )
    db.add(user)
    action = "created"
db.commit()
print(f"Campus administrator {action}: {email}")
