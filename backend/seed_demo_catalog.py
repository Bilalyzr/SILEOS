#!/usr/bin/env python3
"""
Demo catalog seeder for SashaInfinity LMS (local/dev).

Populates the data that the admin "Courses" sub-pages read section-wise:
  - Course Categories  (admin → Courses → Categories)
  - Course Tags        (admin → Courses → Tags)
  - Course Reviews     (admin → Courses → Reviews)
  - Courses, plus the category/tag relation rows and review rows that link
    everything together so each section shows real course information.

Idempotent: re-running it updates/links instead of creating duplicates.

Run:  docker exec sasha_lms-backend-1 python seed_demo_catalog.py
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, InstructorProfile
from app.models.course import (
    Course, CourseCategory, CourseTag, CourseReview, Lesson,
)
from app.models.enrollment import Enrollment


def slugify(text: str) -> str:
    return text.lower().strip().replace(" ", "-").replace("_", "-").replace("&", "and")


def get_or_create_user(db: Session, *, email: str, login: str, name: str, role: str) -> User:
    user = db.query(User).filter(User.user_email == email).first()
    if user:
        return user
    user = User(
        user_login=login,
        user_nicename=slugify(name),
        user_email=email,
        user_pass=get_password_hash("Demo@123456"),
        display_name=name,
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    if role == "instructor":
        db.add(InstructorProfile(user_id=user.id, is_approved=True, is_blocked=False))
        db.flush()
    return user


def get_or_create_category(db: Session, name: str, description: str) -> CourseCategory:
    slug = slugify(name)
    cat = db.query(CourseCategory).filter(CourseCategory.slug == slug).first()
    if not cat:
        cat = CourseCategory(name=name, slug=slug, description=description)
        db.add(cat)
        db.flush()
    return cat


def get_or_create_tag(db: Session, name: str) -> CourseTag:
    slug = slugify(name)
    tag = db.query(CourseTag).filter(CourseTag.slug == slug).first()
    if not tag:
        tag = CourseTag(name=name, slug=slug, description=f"{name} courses")
        db.add(tag)
        db.flush()
    return tag


def get_or_create_course(db: Session, *, author_id: int, title: str, price: float,
                         level: str, primary_category: str) -> Course:
    slug = slugify(title)
    course = db.query(Course).filter(Course.post_name == slug).first()
    if not course:
        course = Course(
            post_author=author_id,
            post_title=title,
            post_name=slug,
            post_content=f"{title} — full curriculum with hands-on projects.",
            post_excerpt=f"Learn {primary_category} with {title}.",
            post_status="publish",
            post_type="courses",
            course_price_type="paid" if price > 0 else "free",
            course_price=price,
            course_level=level,
            course_category=primary_category,
            course_language="English",
        )
        db.add(course)
        db.flush()
    return course


def link(course: Course, categories, tags):
    existing_cat_ids = {c.id for c in course.categories}
    for c in categories:
        if c.id not in existing_cat_ids:
            course.categories.append(c)
    existing_tag_ids = {t.id for t in course.tags}
    for t in tags:
        if t.id not in existing_tag_ids:
            course.tags.append(t)


def get_or_create_review(db: Session, *, course_id: int, user_id: int, rating: int,
                         title: str, content: str, status: str):
    existing = db.query(CourseReview).filter(
        CourseReview.course_id == course_id,
        CourseReview.user_id == user_id,
        CourseReview.review_title == title,
    ).first()
    if existing:
        return existing
    review = CourseReview(
        course_id=course_id,
        user_id=user_id,
        rating=rating,
        review_title=title,
        review_content=content,
        status=status,
        review_status=status,
    )
    db.add(review)
    db.flush()
    return review


def ensure_lessons(db: Session, course: Course, author_id: int, count: int = 3):
    existing = db.query(Lesson).filter(Lesson.post_parent == course.id).count()
    if existing >= count:
        return existing
    for i in range(existing, count):
        db.add(Lesson(
            post_author=author_id,
            post_title=f"Lesson {i + 1}: {course.post_title}",
            post_name=f"{course.post_name}-lesson-{i + 1}",
            post_parent=course.id,
            post_type="lesson",
            post_status="publish",
            menu_order=i + 1,
        ))
    db.flush()
    return count


def enroll(db: Session, *, course: Course, user_id: int, total_lessons: int, progress: int):
    e = db.query(Enrollment).filter(
        Enrollment.course_id == course.id, Enrollment.user_id == user_id,
    ).first()
    completed = round(total_lessons * progress / 100)
    status = "completed" if progress >= 100 else "enrolled"
    if not e:
        e = Enrollment(course_id=course.id, user_id=user_id)
        db.add(e)
    e.enrollment_status = status
    e.course_progress_percentage = progress
    e.total_lessons = total_lessons
    e.completed_lessons = completed
    db.flush()
    return e


def main():
    db = SessionLocal()
    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@sashainfinity.com")
        admin = db.query(User).filter(User.user_email == admin_email).first()
        if not admin:
            print(f"❌ Admin user {admin_email} not found. Run seed_admin_simple.py first.")
            sys.exit(1)

        instructor = get_or_create_user(
            db, email="instructor@sashainfinity.com", login="sasha_instructor",
            name="Sasha Instructor", role="instructor",
        )
        student = get_or_create_user(
            db, email="student@sashainfinity.com", login="sasha_student",
            name="Sasha Student", role="student",
        )

        # Categories
        cats = {
            "Microsoft Excel": get_or_create_category(db, "Microsoft Excel", "Spreadsheet skills, formulas and automation."),
            "Data Analytics": get_or_create_category(db, "Data Analytics", "Turning data into insight."),
            "Data Visualization": get_or_create_category(db, "Data Visualization", "Charts, dashboards and storytelling."),
            "Business Intelligence": get_or_create_category(db, "Business Intelligence", "BI tools and reporting."),
        }

        # Tags
        tags = {
            "Beginner Friendly": get_or_create_tag(db, "Beginner Friendly"),
            "Hands-on Projects": get_or_create_tag(db, "Hands-on Projects"),
            "Certification": get_or_create_tag(db, "Certification"),
            "Formulas & Functions": get_or_create_tag(db, "Formulas & Functions"),
            "Dashboards": get_or_create_tag(db, "Dashboards"),
        }

        # Courses + links
        courses_spec = [
            ("Data Analytics Using Microsoft Excel", 299.0, "beginner", "Microsoft Excel",
             ["Microsoft Excel", "Data Analytics"],
             ["Beginner Friendly", "Formulas & Functions", "Certification"]),
            ("Power BI for Business Intelligence", 399.0, "intermediate", "Business Intelligence",
             ["Business Intelligence", "Data Visualization"],
             ["Dashboards", "Hands-on Projects", "Certification"]),
            ("Excel Dashboards Masterclass", 199.0, "intermediate", "Microsoft Excel",
             ["Microsoft Excel", "Data Visualization"],
             ["Dashboards", "Hands-on Projects"]),
            ("Python for Data Analytics", 499.0, "advanced", "Data Analytics",
             ["Data Analytics"],
             ["Hands-on Projects", "Certification"]),
        ]

        created_courses = {}
        for title, price, level, primary, cat_names, tag_names in courses_spec:
            course = get_or_create_course(
                db, author_id=instructor.id, title=title, price=price,
                level=level, primary_category=primary,
            )
            link(course, [cats[c] for c in cat_names], [tags[t] for t in tag_names])
            created_courses[title] = course
        db.flush()

        # Reviews (mix of statuses; page defaults to 'pending')
        reviews_spec = [
            ("Data Analytics Using Microsoft Excel", student.id, 5, "Excellent course",
             "Clear explanations and great hands-on exercises.", "pending"),
            ("Data Analytics Using Microsoft Excel", admin.id, 4, "Very useful",
             "Covered everything I needed for my job.", "approved"),
            ("Power BI for Business Intelligence", student.id, 5, "Loved the dashboards",
             "The BI projects were really practical.", "pending"),
            ("Excel Dashboards Masterclass", student.id, 4, "Good masterclass",
             "Learned a lot about interactive dashboards.", "approved"),
            ("Python for Data Analytics", student.id, 5, "Advanced and thorough",
             "Perfect follow-up after the Excel course.", "pending"),
        ]
        for title, uid, rating, rtitle, content, status in reviews_spec:
            course = created_courses[title]
            get_or_create_review(db, course_id=course.id, user_id=uid, rating=rating,
                                 title=rtitle, content=content, status=status)

        # Lessons + enrollments (so the student dashboard shows course content).
        # Enroll the demo student with varied progress: completed / in-progress / not-started.
        enroll_spec = [
            ("Data Analytics Using Microsoft Excel", 100),
            ("Power BI for Business Intelligence", 40),
            ("Excel Dashboards Masterclass", 0),
        ]
        for title, progress in enroll_spec:
            course = created_courses[title]
            n = ensure_lessons(db, course, instructor.id, count=3)
            enroll(db, course=course, user_id=student.id, total_lessons=n, progress=progress)

        db.commit()

        # Summary
        print("✅ Demo catalog seeded.")
        print(f"   Categories: {db.query(CourseCategory).count()}")
        print(f"   Tags:       {db.query(CourseTag).count()}")
        print(f"   Courses:    {db.query(Course).count()}")
        print(f"   Reviews:    {db.query(CourseReview).count()}")
        for c in db.query(Course).all():
            print(f"   - {c.post_title}: categories={[x.name for x in c.categories]} tags={[x.name for x in c.tags]}")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
