"""Local-only synthetic campus preview. Never reads production environment files.

Run from the repository root using backend/.venv/Scripts/python scripts/preview_campus.py.
The preview binds to loopback and keeps its database and credentials in ignored .local/.
"""
import os
from pathlib import Path
import json
import pyotp
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

root = Path(__file__).resolve().parents[1]
local = Path(os.environ.get("SASHA_PREVIEW_ROOT", str(root / ".local"))).resolve()
if not local.is_relative_to((root / ".local").resolve()):
    raise RuntimeError("Synthetic preview files must remain inside this workspace's .local directory")
local.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root / "backend"))
os.environ.update(
    {
        "FRONTEND_URL": "http://127.0.0.1:3000",
        "SMTP_HOST": "",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "CAMPUS_CAMPUS_PLAN_ID": "",
        "CAMPUS_ENTERPRISE_PLAN_ID": "",
        "WHATSAPP_PHONE_NUMBER_ID": "",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "",
        "WHATSAPP_BUSINESS_PHONE": "",
        "WHATSAPP_ACCESS_TOKEN": "",
        "WHATSAPP_APP_SECRET": "",
        "WHATSAPP_VERIFY_TOKEN": "",
        "WHATSAPP_APPROVED_TEMPLATES": "",
        "DATABASE_URL": "sqlite:///" + (local / "campus-preview.sqlite").as_posix(),
        "REDIS_URL": "redis://127.0.0.1:6399/0",
        "SECRET_KEY": "local-preview-" + "x" * 64,
        "JWT_SECRET": "local-preview-" + "y" * 64,
        "VIDEO_SECRET": "local-preview-video-" + "z" * 40,
        "ENVIRONMENT": "development",
        "DEBUG": "true",
        "ADMIN_PASSWORD": secrets.token_urlsafe(32),
        "RAZORPAY_KEY": "",
        "RAZORPAY_SECRET": "",
        "RAZORPAY_KEY_ID": "",
        "RAZORPAY_KEY_SECRET": "",
        "ENABLE_API_RATE_LIMITING": "false",
        "ENABLE_REQUEST_LOGGING": "false",
        "ENABLE_IP_WHITELISTING": "false",
        "ALLOWED_HOSTS": '["127.0.0.1","localhost","testserver"]',
        "ALLOWED_ORIGINS": '["http://localhost:3000","http://127.0.0.1:3000"]',
    }
)

from app.core.database import Base, engine, SessionLocal, reconcile_business_verticals

engine.echo = False
from app import models
from app.core.security import get_password_hash
from app.models.user import User, UserProfile, InstructorProfile
from app.models.institution import (
    Institution,
    InstitutionMember,
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionCourse,
    InstitutionAssignment,
    InstitutionAudit,
)
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.cohort import College, Cohort
from app.models.company import Company
from app.models.company_dashboard import CompanyManager
from app.models.campus_operations import ParentLinkRequest
from app.routers.parents import ParentStudent

Base.metadata.create_all(engine)
reconcile_business_verticals()
with SessionLocal() as db:
    owner = db.query(User).filter_by(user_email="campus-owner@example.org").first()
    if not owner:
        password = secrets.token_urlsafe(20) + "Aa1!"
        owner = User(
            user_login="campus_preview_owner",
            user_nicename="campus-owner",
            user_email="campus-owner@example.org",
            user_pass=get_password_hash(password),
            display_name="Ananya Rao",
            role="instructor",
            is_active=True,
            is_verified=True,
            profile_completed=True,
        )
        db.add(owner)
        db.flush()
        db.add(UserProfile(user_id=owner.id, first_name="Ananya", last_name="Rao"))
        db.add(InstructorProfile(user_id=owner.id, is_approved=True))
        inst = Institution(
            name="Greenwood College",
            slug="greenwood-preview",
            kind="college",
            academic_year="2026–2027",
            timezone="Asia/Kolkata",
            description="Synthetic local preview data for the Campus interface.",
            plan="starter",
        )
        db.add(inst)
        db.flush()
        db.add(
            InstitutionMember(
                institution_id=inst.id,
                user_id=owner.id,
                role="owner",
                status="active",
                department="Academic office",
            )
        )
        courses = []
        for title in (
            "Foundations of Physics",
            "Mathematics for Discovery",
            "Introduction to Computer Science",
            "Environmental Studies",
        ):
            course = Course(
                post_author=owner.id,
                post_title=title,
                post_status="published",
                course_price_type="free",
                post_name=title.lower().replace(" ", "-"),
                course_type="utporul",
            )
            db.add(course)
            db.flush()
            link = InstitutionCourse(
                institution_id=inst.id, course_id=course.id, connected_by=owner.id
            )
            db.add(link)
            db.flush()
            courses.append((course, link))
        batches = []
        for name, department in (
            ("B.Sc. Physics · Year 1", "Science"),
            ("B.Sc. Mathematics · Year 1", "Mathematics"),
            ("B.Tech. Computer Science", "Engineering"),
        ):
            b = InstitutionBatch(
                institution_id=inst.id,
                name=name,
                department=department,
                academic_year="2026–2027",
            )
            db.add(b)
            db.flush()
            batches.append(b)
        names = (
            "Aarav Kumar",
            "Diya Shah",
            "Ishaan Patel",
            "Meera Nair",
            "Rohan Das",
            "Sara Ali",
            "Kavya Rao",
            "Aditya Sen",
            "Nisha Menon",
            "Dev Sharma",
            "Priya Iyer",
            "Arjun Reddy",
        )
        for n, name in enumerate(names):
            u = User(
                user_login=f"campus_student_{n}",
                user_nicename=f"campus-student-{n}",
                user_email=f"campus-student-{n}@example.org",
                user_pass=get_password_hash(secrets.token_urlsafe(24)),
                display_name=name,
                role="student",
                is_active=True,
                is_verified=True,
                profile_completed=True,
            )
            db.add(u)
            db.flush()
            m = InstitutionMember(
                institution_id=inst.id,
                user_id=u.id,
                role="student",
                status="active",
                department=batches[n % 3].department,
            )
            db.add(m)
            db.flush()
            db.add(InstitutionBatchMember(batch_id=batches[n % 3].id, member_id=m.id))
            db.add(
                Enrollment(
                    user_id=u.id,
                    course_id=courses[n % 3][0].id,
                    enrollment_status="enrolled",
                    course_progress_percentage=[100, 65, 42, 85, 100, 18][n % 6],
                )
            )
        for n, b in enumerate(batches):
            db.add(
                InstitutionAssignment(
                    batch_id=b.id,
                    institution_course_id=courses[n][1].id,
                    due_date="2026-11-30",
                )
            )
        for action, detail in (
            ("institution.created", "Greenwood College workspace created"),
            ("batch.created", "Three academic batches are ready"),
            ("course.connected", "Four foundation courses connected"),
            ("batch.members_added", "Twelve students joined their learning groups"),
        ):
            db.add(
                InstitutionAudit(
                    institution_id=inst.id,
                    actor_id=owner.id,
                    action=action,
                    detail=detail,
                )
            )
        db.commit()
        (local / "campus-preview-login.txt").write_text(
            f"campus-owner@example.org\n{password}\n", encoding="utf-8"
        )


def provision_preview_accounts() -> list[dict[str, str]]:
    """Create one usable local login for every SashaInfinity account role.

    Credentials live only under the ignored ``.local`` directory. Existing
    preview credentials are deliberately reused so restarting this script does
    not surprise anyone who is already testing the interface.
    """

    manifest_path = local / "campus-role-logins.json"
    owner_login_path = local / "campus-preview-login.txt"

    try:
        existing_records = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(existing_records, list):
            existing_records = []
    except (FileNotFoundError, json.JSONDecodeError):
        existing_records = []

    existing_by_email = {
        row.get("email"): row
        for row in existing_records
        if isinstance(row, dict) and row.get("email")
    }
    shared_password = next(
        (
            row.get("password")
            for row in existing_records
            if row.get("email") != "campus-owner@example.org" and row.get("password")
        ),
        None,
    ) or ("Campus-" + secrets.token_hex(5) + "!Aa1")

    owner_password = None
    try:
        owner_lines = owner_login_path.read_text(encoding="utf-8").splitlines()
        if len(owner_lines) >= 2 and owner_lines[0] == "campus-owner@example.org":
            owner_password = owner_lines[1]
    except FileNotFoundError:
        pass

    specs = (
        {
            "role": "Institution owner",
            "email": "campus-owner@example.org",
            "account_role": "instructor",
            "workspace_role": "owner",
            "display_name": "Ananya Rao",
            "landing_path": "/institutions",
        },
        {
            "role": "Campus administrator",
            "email": "campus-admin@example.org",
            "account_role": "instructor",
            "workspace_role": "admin",
            "display_name": "Preview Campus Administrator",
            "landing_path": "/institutions",
        },
        {
            "role": "Teacher",
            "email": "campus-teacher@example.org",
            "account_role": "instructor",
            "workspace_role": "teacher",
            "display_name": "Preview Teacher",
            "landing_path": "/instructor/dashboard",
        },
        {
            "role": "Student",
            "email": "campus-student-0@example.org",
            "account_role": "student",
            "workspace_role": "student",
            "display_name": "Aarav Kumar",
            "landing_path": "/dashboard",
        },
        {
            "role": "Parent / guardian",
            "email": "campus-parent@example.org",
            "account_role": "parent",
            "display_name": "Preview Parent / Guardian",
            "landing_path": "/parent",
        },
        {
            "role": "SPOC",
            "email": "campus-spoc@example.org",
            "account_role": "spoc",
            "display_name": "Preview Campus SPOC",
            "landing_path": "/spoc/dashboard",
        },
        {
            "role": "Company owner",
            "email": "company-owner@example.org",
            "account_role": "company",
            "display_name": "Preview Company Owner",
            "landing_path": "/company/dashboard",
        },
        {
            "role": "Company manager",
            "email": "company-manager@example.org",
            "account_role": "company_manager",
            "display_name": "Preview Company Manager",
            "landing_path": "/company/dashboard",
        },
        {
            "role": "Platform administrator",
            "email": "platform-admin@example.org",
            "account_role": "admin",
            "display_name": "Preview Platform Administrator",
            "landing_path": "/admin/operations",
        },
        {
            "role": "Super administrator",
            "email": "platform-superadmin@example.org",
            "account_role": "superadmin",
            "display_name": "Preview Super Administrator",
            "landing_path": "/superadmin/dashboard",
        },
    )

    accounts: dict[str, User] = {}
    mfa_secrets: dict[str, str] = {}
    with SessionLocal() as db:
        institution = db.query(Institution).filter_by(slug="greenwood-preview").one()

        for spec in specs:
            email = spec["email"]
            user = db.query(User).filter_by(user_email=email).first()
            if user is None:
                login = email.split("@", 1)[0].replace("-", "_")
                user = User(
                    user_login=login,
                    user_nicename=email.split("@", 1)[0],
                    user_email=email,
                    user_pass=get_password_hash(shared_password),
                    display_name=spec["display_name"],
                    role=spec["account_role"],
                )
                db.add(user)
                db.flush()

            user.display_name = spec["display_name"]
            user.role = spec["account_role"]
            user.is_active = True
            user.user_status = 1
            user.is_verified = True
            user.profile_completed = True

            if email == "campus-owner@example.org":
                if owner_password is None:
                    owner_password = secrets.token_urlsafe(20) + "Aa1!"
                    owner_login_path.write_text(
                        f"{email}\n{owner_password}\n", encoding="utf-8"
                    )
                    user.user_pass = get_password_hash(owner_password)
            else:
                user.user_pass = get_password_hash(shared_password)

            if user.profile is None:
                names = spec["display_name"].split(" ", 1)
                db.add(
                    UserProfile(
                        user_id=user.id,
                        first_name=names[0],
                        last_name=names[1] if len(names) > 1 else "",
                    )
                )

            if spec["account_role"] == "instructor" and user.instructor_profile is None:
                db.add(InstructorProfile(user_id=user.id, is_approved=True))
            elif spec["account_role"] == "instructor":
                user.instructor_profile.is_approved = True

            if spec["account_role"] in ("admin", "superadmin"):
                existing_secret = existing_by_email.get(email, {}).get(
                    "authenticator_setup_key"
                )
                user.totp_secret = existing_secret or user.totp_secret
                try:
                    if not user.totp_secret:
                        raise ValueError("missing preview TOTP secret")
                    pyotp.TOTP(user.totp_secret).now()
                except Exception:
                    user.totp_secret = pyotp.random_base32()
                user.totp_enabled = True
                mfa_secrets[email] = user.totp_secret

            workspace_role = spec.get("workspace_role")
            if workspace_role:
                membership = (
                    db.query(InstitutionMember)
                    .filter_by(institution_id=institution.id, user_id=user.id)
                    .first()
                )
                if membership is None:
                    db.add(
                        InstitutionMember(
                            institution_id=institution.id,
                            user_id=user.id,
                            role=workspace_role,
                            status="active",
                            department="Academic office",
                        )
                    )
                else:
                    membership.role = workspace_role
                    membership.status = "active"

            accounts[email] = user

        owner = accounts["campus-owner@example.org"]
        student = accounts["campus-student-0@example.org"]
        parent = accounts["campus-parent@example.org"]
        spoc = accounts["campus-spoc@example.org"]
        company_owner = accounts["company-owner@example.org"]
        company_manager = accounts["company-manager@example.org"]

        company = db.query(Company).filter_by(owner_user_id=company_owner.id).first()
        if company is None:
            company = Company(
                owner_user_id=company_owner.id,
                name="Sasha Preview Technologies",
                slug="sasha-preview-technologies",
                contact_email=company_owner.user_email,
                industry="Education technology",
                team_size="11-50",
                description="Synthetic local company workspace for role previews.",
                is_approved=True,
                approval_source="admin_invite",
                approved_by=accounts["platform-admin@example.org"].id,
                approved_at=datetime.now(timezone.utc),
            )
            db.add(company)
            db.flush()
        else:
            company.is_approved = True

        manager_link = (
            db.query(CompanyManager).filter_by(user_id=company_manager.id).first()
        )
        if manager_link is None:
            db.add(
                CompanyManager(
                    company_id=company.id,
                    user_id=company_manager.id,
                    invited_by=company_owner.id,
                    accepted_at=datetime.now(timezone.utc),
                )
            )
        else:
            manager_link.company_id = company.id
            manager_link.accepted_at = manager_link.accepted_at or datetime.now(
                timezone.utc
            )

        college = db.query(College).filter_by(slug="greenwood-career-preview").first()
        if college is None:
            college = College(
                name="Greenwood College Career Office",
                slug="greenwood-career-preview",
                city="Bengaluru",
                state="Karnataka",
                contact_name=spoc.display_name,
                contact_email=spoc.user_email,
                created_by=owner.id,
            )
            db.add(college)
            db.flush()

        cohort = (
            db.query(Cohort)
            .filter_by(spoc_user_id=spoc.id, slug="greenwood-placement-preview")
            .first()
        )
        if cohort is None:
            preview_course = (
                db.query(Course).filter(Course.post_author == owner.id).first()
            )
            db.add(
                Cohort(
                    college_id=college.id,
                    course_id=preview_course.id if preview_course else None,
                    spoc_user_id=spoc.id,
                    name="Greenwood Placement Cohort",
                    slug="greenwood-placement-preview",
                    max_students=60,
                    is_active=True,
                )
            )

        parent_request = (
            db.query(ParentLinkRequest)
            .filter_by(parent_user_id=parent.id, student_user_id=student.id)
            .first()
        )
        if parent_request is None:
            db.add(
                ParentLinkRequest(
                    parent_user_id=parent.id,
                    student_user_id=student.id,
                    status="approved",
                )
            )
        else:
            parent_request.status = "approved"
        if (
            db.query(ParentStudent)
            .filter_by(parent_user_id=parent.id, student_user_id=student.id)
            .first()
            is None
        ):
            db.add(ParentStudent(parent_user_id=parent.id, student_user_id=student.id))

        db.commit()

    records = []
    for spec in specs:
        email = spec["email"]
        row = {
            "role": spec["role"],
            "account_role": spec["account_role"],
            "email": email,
            "password": owner_password
            if email == "campus-owner@example.org"
            else shared_password,
            "landing_path": spec["landing_path"],
        }
        if spec.get("workspace_role"):
            row["workspace_role"] = spec["workspace_role"]
        if email in mfa_secrets:
            row["authenticator_setup_key"] = mfa_secrets[email]
        records.append(row)

    manifest_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


provision_preview_accounts()


def seed_sasha_learning_monitor() -> None:
    """Give the local instructor preview realistic, non-production evidence."""
    from app.models.tutor_learning_signal import TutorLearningSignal

    concept_sets = {
        "Foundations of Physics": ("projectile motion", "vectors", "force and acceleration"),
        "Mathematics for Discovery": ("quadratic equations", "trigonometry", "fractions"),
        "Introduction to Computer Science": ("loops and iteration", "variables", "algorithm tracing"),
        "Environmental Studies": ("carbon cycle", "ecosystem balance", "waste segregation"),
    }
    prompts = (
        ("I am still confused. Can you explain {concept} again with a simpler example?", 91.0, "high", "repeated_confusion", 3),
        ("How do I apply {concept} step by step to this problem?", 74.0, "watch", "application_gap", 2),
        ("What is the meaning of {concept}, and how is it different from the last topic?", 58.0, "watch", "terminology_gap", 1),
        ("I am not sure whether I understand {concept}. Can you check me?", 43.0, "developing", "confidence_gap", 0),
    )
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        students = db.query(User).filter(User.role == "student").order_by(User.id).limit(8).all()
        if not students:
            return
        courses = db.query(Course).filter(Course.post_title.in_(concept_sets)).all()
        for course in courses:
            if db.query(TutorLearningSignal.id).filter(TutorLearningSignal.course_id == course.id).first():
                continue
            concepts = concept_sets[course.post_title]
            for index, (template, score, severity, gap, repeats) in enumerate(prompts):
                student = students[index % len(students)]
                concept = concepts[index % len(concepts)]
                db.add(TutorLearningSignal(
                    user_id=student.id,
                    course_id=course.id,
                    session_key=f"preview-{course.id}-{student.id}",
                    prompt_excerpt=template.format(concept=concept),
                    concept=concept,
                    struggle_score=score,
                    severity=severity,
                    likely_gap=gap,
                    reasons=[
                        "The learner explicitly described confusion or uncertainty.",
                        f"This concept appeared in {repeats} earlier Sasha questions." if repeats else "A course-linked explanation request was recorded for follow-up evidence.",
                    ],
                    repeat_count=repeats,
                    created_at=now - timedelta(hours=index * 7 + course.id),
                ))
            db.commit()


seed_sasha_learning_monitor()

from app.main import app


@asynccontextmanager
async def preview_lifespan(_app):
    # No production seed jobs, reconciliations, or provider integrations in preview.
    yield


app.router.lifespan_context = preview_lifespan
if __name__ == "__main__":
    import uvicorn

    print(
        "Local synthetic Campus preview: http://127.0.0.1:8000; credentials in .local/campus-role-logins.json"
    )
    uvicorn.run(app, host="127.0.0.1", port=8000)
