#!/usr/bin/env python3
"""
Seed mock issued certificates for a student — testing utility.

Purpose: quickly create a few completed enrollments + issued certificates for
a student so you can verify that the **downloaded** PDF now matches the
**on-screen preview** (both use the certificates/template.html design after the
HTML-to-PDF fix).

For each created certificate the script prints:
  * the in-app certificate page         (/certificates/{course_id})
  * the preview / verify page (Design B) (/api/v1/certificates/verify-certificate?id=..&hash=..)
  * the PDF download endpoint            (/api/v1/certificates/download-html-pdf/{id}/{hash})

Open the preview and the download for the same certificate — they should be the
same design.

Usage (inside the backend container, or anywhere the DB is reachable):

    docker-compose exec backend python seed_mock_certificates.py
    docker-compose exec backend python seed_mock_certificates.py --email student@example.com --count 3
    STUDENT_EMAIL=student@example.com python seed_mock_certificates.py

Idempotent: re-running will not duplicate a certificate for a (user, course)
pair — the existing one is reused and printed.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `app...` importable when run from the backend/ directory.
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.certificate import Certificate, IssuedCertificate
from app.services.certificate_service import CertificateService

settings = get_settings()


def resolve_student(db: Session, email: str | None) -> User | None:
    """Find the target student: by email if given, else the first 'student'."""
    if email:
        user = db.query(User).filter(User.user_email == email).first()
        if not user:
            print(f"❌ No user found with email {email!r}")
        return user

    user = db.query(User).filter(User.role == "student").order_by(User.id).first()
    if not user:
        # Fall back to any non-admin user.
        user = db.query(User).filter(User.role != "admin").order_by(User.id).first()
    return user


def ensure_template_id(db: Session) -> int:
    """
    Return a valid certificates.id to satisfy IssuedCertificate.certificate_id
    (FK). Reuse an existing template, or create a minimal default one.
    """
    template = db.query(Certificate).order_by(Certificate.id).first()
    if template:
        return template.id

    # No template exists — create a minimal default one. post_author is a
    # NOT NULL FK, so point it at any admin (or the first user).
    author = db.query(User).filter(User.role == "admin").order_by(User.id).first()
    if not author:
        author = db.query(User).order_by(User.id).first()
    if not author:
        raise RuntimeError("Cannot create a certificate template: no users exist.")

    template = Certificate(
        post_author=author.id,
        post_title="Default Certificate Template",
        post_status="publish",
        post_type="tutor_certificates",
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    print(f"ℹ️  Created default certificate template (id={template.id})")
    return template.id


def pick_courses(db: Session, count: int) -> list[Course]:
    """Pick up to `count` courses to certify the student against."""
    courses = (
        db.query(Course)
        .filter(Course.post_status.in_(["publish", "published"]))
        .order_by(Course.id)
        .limit(count)
        .all()
    )
    if not courses:
        # No published courses — just take whatever exists.
        courses = db.query(Course).order_by(Course.id).limit(count).all()
    return courses


def upsert_completed_enrollment(db: Session, user: User, course: Course) -> Enrollment:
    """Ensure the student has a *completed* enrollment for the course."""
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id)
        .first()
    )
    now = datetime.now(timezone.utc)
    if not enrollment:
        enrollment = Enrollment(
            user_id=user.id,
            course_id=course.id,
            enrollment_status="completed",
            course_progress_percentage=100,
            completion_date=now,
        )
        db.add(enrollment)
    else:
        enrollment.enrollment_status = "completed"
        enrollment.course_progress_percentage = 100
        if enrollment.completion_date is None:
            enrollment.completion_date = now
    db.commit()
    db.refresh(enrollment)
    return enrollment


def issue_mock_certificate(
    db: Session, user: User, course: Course, template_id: int
) -> tuple[IssuedCertificate, bool]:
    """Create (or reuse) an IssuedCertificate for (user, course)."""
    existing = (
        db.query(IssuedCertificate)
        .filter(
            IssuedCertificate.user_id == user.id,
            IssuedCertificate.course_id == course.id,
        )
        .first()
    )
    if existing:
        return existing, False

    enrollment = upsert_completed_enrollment(db, user, course)

    certificate_hash = CertificateService.generate_verification_code()
    secure_cert_id = CertificateService.generate_secure_certificate_id(
        user_id=user.id,
        course_id=course.id,
        issue_date=enrollment.completion_date,
    )

    cert = IssuedCertificate(
        certificate_id=template_id,
        course_id=course.id,
        user_id=user.id,
        certificate_hash=certificate_hash,
        secure_certificate_id=secure_cert_id,
        certificate_title=f"Certificate of Completion - {course.post_title}",
        certificate_content="",
        completion_date=enrollment.completion_date,
        course_completion_percentage=100,
        certificate_download_url="",
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    # Stamp the enrollment so it shows as certified in the dashboard.
    enrollment.certificate_id = str(cert.id)
    db.commit()

    return cert, True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed mock issued certificates for a student.")
    parser.add_argument("--email", default=os.getenv("STUDENT_EMAIL"), help="Target student email")
    parser.add_argument("--count", type=int, default=3, help="How many certificates to create")
    args = parser.parse_args()

    base_url = getattr(settings, "FRONTEND_URL", "https://lms.sashainfinity.com").rstrip("/")

    db: Session = SessionLocal()
    try:
        student = resolve_student(db, args.email)
        if not student:
            print("❌ Could not resolve a student to issue certificates to.")
            sys.exit(1)

        print(f"🎓 Issuing mock certificates to: {student.display_name} <{student.user_email}> (id={student.id})")

        template_id = ensure_template_id(db)

        courses = pick_courses(db, args.count)
        if not courses:
            print("❌ No courses found in the database to certify against.")
            sys.exit(1)

        created = 0
        print("\n" + "=" * 80)
        for course in courses:
            cert, is_new = issue_mock_certificate(db, student, course, template_id)
            created += 1 if is_new else 0
            tag = "CREATED" if is_new else "EXISTS "
            verify = f"{base_url}/api/v1/certificates/verify-certificate?id={cert.secure_certificate_id}&hash={cert.certificate_hash}"
            download = f"{base_url}/api/v1/certificates/download-html-pdf/{cert.secure_certificate_id}/{cert.certificate_hash}"
            page = f"{base_url}/certificates/{course.id}"
            print(f"[{tag}] {course.post_title}  (cert id={cert.id})")
            print(f"        In-app page : {page}")
            print(f"        Preview     : {verify}")
            print(f"        Download PDF: {download}")
            print("-" * 80)

        print(f"\n✅ Done. {created} new certificate(s) created, {len(courses) - created} already existed.")
        print("   Open the Preview and the Download PDF for the same certificate — they should match.")
    except Exception as exc:
        db.rollback()
        print(f"❌ Failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
