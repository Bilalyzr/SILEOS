"""One-off local-dev seeder: one demo account per role + the rows each role
needs to be usable (approved InstructorProfile, approved Company, manager link).
"""
from datetime import datetime

from app.core import totp
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.company import Company
from app.models.company_dashboard import CompanyManager
from app.models.user import InstructorProfile, User

PW = "TestPass@2026"
now = datetime.utcnow()

ACCOUNTS = [
    # (role, login, email, display)
    ("student", "student_demo", "student@sashalms.test", "Demo Student"),
    ("instructor", "instructor_demo", "instructor@sashalms.test", "Demo Instructor"),
    ("spoc", "spoc_demo", "spoc@sashalms.test", "Demo Spoc"),
    ("company", "company_demo", "company@sashalms.test", "Demo Company Owner"),
    ("company_manager", "manager_demo", "manager@sashalms.test", "Demo Company Manager"),
    ("superadmin", "superadmin_demo", "superadmin@sashalms.test", "Demo Superadmin"),
]

db = SessionLocal()
hashed = get_password_hash(PW)
company_user = None

for role, login, email, display in ACCOUNTS:
    if db.query(User).filter(User.user_email == email).first():
        print(f"skip (exists): {email}")
        continue
    u = User(
        user_login=login,
        user_pass=hashed,
        user_nicename=login,
        user_email=email,
        user_url="",
        user_activation_key="",
        user_status=0,
        display_name=display,
        role=role,
        is_active=True,
        is_verified=True,
        profile_completed=True,
        last_login=now,
        user_registered=now,
        created_at=now,
        updated_at=now,
        totp_secret="",
        totp_enabled=False,
    )
    db.add(u)
    db.flush()

    if role == "instructor":
        db.add(InstructorProfile(user_id=u.id, is_approved=True))
    elif role == "superadmin":
        u.totp_secret = totp.generate_secret()
        u.totp_enabled = True
    elif role == "company":
        company_user = u
        db.add(
            Company(
                owner_user_id=u.id,
                name="Demo Technologies Pvt Ltd",
                slug="demo-technologies",
                contact_email=email,
                is_approved=True,
                approval_source="admin_invite",
            )
        )
    print(f"created {role}: {email} (user_id={u.id})")

mgr = db.query(User).filter(User.role == "company_manager").first()
comp = db.query(Company).filter(Company.slug == "demo-technologies").first()
if mgr and comp:
    link = (
        db.query(CompanyManager)
        .filter(CompanyManager.user_id == mgr.id)
        .first()
    )
    if not link:
        db.add(CompanyManager(company_id=comp.id, user_id=mgr.id, accepted_at=now))
        print(f"linked manager (user_id={mgr.id}) to company '{comp.name}'")

db.commit()

sa = db.query(User).filter(User.role == "superadmin").first()
if sa:
    print("SUPERADMIN_TOTP_SECRET:", sa.totp_secret)
    print("SUPERADMIN_OTPAUTH:", totp.provisioning_uri(sa.totp_secret, sa.user_email))
db.close()
