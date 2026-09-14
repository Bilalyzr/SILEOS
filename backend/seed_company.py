"""
Seed a pre-approved Company login for local development.

Creates (or updates) a User(role='company', is_verified=True) and a linked
Company(is_approved=True), then prints the credentials.

Run inside the backend container:
    docker-compose exec backend python seed_company.py
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.company import Company


EMAIL = "company@example.com"
PASSWORD = "Company@123"
LOGIN = "demo_company"
DISPLAY_NAME = "Demo Company"
COMPANY_NAME = "Demo Company Pvt Ltd"
SLUG = "demo-company"


def main() -> None:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.user_email == EMAIL).first()
        if user:
            user.role = "company"
            user.user_pass = get_password_hash(PASSWORD)
            user.is_active = True
            user.is_verified = True
            user.display_name = DISPLAY_NAME
            print(f"Updated existing user id={user.id}")
        else:
            user = User(
                user_login=LOGIN,
                user_pass=get_password_hash(PASSWORD),
                user_nicename=LOGIN,
                user_email=EMAIL,
                display_name=DISPLAY_NAME,
                role="company",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            print(f"Created user id={user.id}")

        company = db.query(Company).filter(Company.owner_user_id == user.id).first()
        if company:
            company.name = COMPANY_NAME
            company.slug = SLUG
            company.contact_email = EMAIL
            company.is_approved = True
            company.approval_source = "admin_invite"
            company.approved_at = datetime.utcnow()
            company.industry = "Technology"
            company.team_size = "11-50"
            company.description = "Pre-seeded demo company for local development."
            print(f"Updated existing company id={company.id}")
        else:
            # Ensure slug is unique
            base_slug = SLUG
            slug = base_slug
            n = 2
            while db.query(Company).filter(Company.slug == slug).first() is not None:
                slug = f"{base_slug}-{n}"
                n += 1

            company = Company(
                owner_user_id=user.id,
                name=COMPANY_NAME,
                slug=slug,
                contact_email=EMAIL,
                is_approved=True,
                approval_source="admin_invite",
                approved_at=datetime.utcnow(),
                industry="Technology",
                team_size="11-50",
                description="Pre-seeded demo company for local development.",
            )
            db.add(company)
            print(f"Created company slug={slug}")

        db.commit()

        print("\n=== Company Login Ready ===")
        print(f"  URL:      http://localhost:3100/login")
        print(f"  Email:    {EMAIL}")
        print(f"  Password: {PASSWORD}")
        print(f"  Redirect: /company/dashboard")
    except Exception as e:
        db.rollback()
        print(f"FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
