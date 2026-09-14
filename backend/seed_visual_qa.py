"""Seed a throwaway SQLite DB with catalog content for visual QA.

Run:  DATABASE_URL=sqlite:///./visual_qa.db ... python seed_visual_qa.py
Then start uvicorn with the same DATABASE_URL. NOT for production.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./visual_qa.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "visual-qa-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app import models  # noqa: F401,E402  (register all tables)
from app.models.user import User  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.bundle import Bundle, BundleCourse  # noqa: E402
from app.models.membership import MembershipPlan, MembershipPlanCourse  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(Course).count() == 0:
    author = User(
        user_login="qa_instructor",
        user_pass="x",
        user_nicename="qa-instructor",
        user_email="qa_instructor@example.com",
        display_name="Priya Raman",
    )
    db.add(author)
    db.flush()

    course_specs = [
        ("Full-Stack Web Development Bootcamp", 4999.0,
         "Build and deploy real web applications with React and FastAPI."),
        ("Python for Data Analysis", 2999.0,
         "From spreadsheets to pandas — practical data skills for working professionals."),
        ("UI/UX Design Fundamentals", 2499.0,
         "Design interfaces people love, from wireframe to polished handoff."),
        ("Cloud & DevOps Essentials", 3999.0,
         "Docker, CI/CD and cloud deployment for modern teams."),
    ]
    courses = []
    for title, price, excerpt in course_specs:
        c = Course(
            post_author=author.id,
            post_title=title,
            post_status="publish",
            course_price_type="paid",
            course_price=price,
        )
        for attr, val in (("post_excerpt", excerpt), ("post_content", excerpt)):
            if hasattr(c, attr):
                setattr(c, attr, val)
        db.add(c)
        courses.append(c)
    db.flush()

    plan = MembershipPlan(
        name="All-Access Pro",
        description="Every paid course, one simple subscription. Cancel anytime.",
        all_access=True,
        period="monthly",
        interval=1,
        price=1499.0,
        razorpay_plan_id="plan_VISUALQA1",
    )
    starter = MembershipPlan(
        name="Starter",
        description="Our two most popular career-starter courses.",
        all_access=False,
        period="monthly",
        interval=1,
        price=799.0,
        razorpay_plan_id="plan_VISUALQA2",
    )
    db.add_all([plan, starter])
    db.flush()
    db.add_all([
        MembershipPlanCourse(plan_id=starter.id, course_id=courses[0].id),
        MembershipPlanCourse(plan_id=starter.id, course_id=courses[1].id),
    ])

    bundle = Bundle(
        name="Career Starter Pack",
        slug="career-starter-pack",
        description="Web development + data analysis together — everything you "
                    "need for your first tech role, at one discounted price.",
        bundle_price=5999.0,
    )
    db.add(bundle)
    db.flush()
    db.add_all([
        BundleCourse(bundle_id=bundle.id, course_id=courses[0].id),
        BundleCourse(bundle_id=bundle.id, course_id=courses[1].id),
    ])
    db.commit()
    print(f"Seeded: {len(courses)} courses, 2 plans, 1 bundle")
else:
    print("Already seeded")
db.close()
