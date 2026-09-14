#!/usr/bin/env python3
"""
Refresh the QR / verification link on EVERY already-issued certificate.

Background: the QR baked into certificates used to encode a broken verification
URL (wrong domain + backend `/api/v1/...` path + query-param form), so scanning
it 404'd. The generators now emit the clean public portal link
`{FRONTEND_URL}/verify-certificate/{certificate_hash}`. New certificates pick
this up automatically; this script back-fills every EXISTING certificate.

For each IssuedCertificate it:
  1. Clears the cached HTML-rendered PDF (`cert_html_*.pdf`) and PNG
     (`cert_img_*.png`) so the on-screen view and the HTML-PDF download
     re-render on next access straight from the (now-fixed) verify page.
  2. Rebuilds the ReportLab static PDF (`certificate_download_url`) in place —
     the file behind the verify page's "View Original / Download Certificate"
     buttons — with the corrected QR.

Crucially it does NOT touch `certificate_hash` / `secure_certificate_id`, so
every previously shared verification link keeps resolving to the same
certificate; only the embedded QR/link is corrected.

Idempotent: safe to run repeatedly.

Usage (must run where the Linux cert dirs + /tmp exist — i.e. the backend
container, since the ReportLab renderer writes /tmp/qr_*.png):

    docker-compose exec backend python refresh_certificate_qr.py
    docker-compose exec backend python refresh_certificate_qr.py --dry-run
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

# Make `app...` importable when run from the backend/ directory.
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models.user import User
from app.models.course import Course
from app.models.certificate import IssuedCertificate
from app.services.certificate_service import CertificateService

CERT_DIR = "certificates"


def _static_pdf_path(cert) -> str:
    """Reuse the existing static-PDF filename when present, else mint a new one.

    Keeping the same filename means the stored `certificate_download_url` (and
    any link already pointing at it) stays valid — we just overwrite the file
    contents with the corrected-QR render.
    """
    url = cert.certificate_download_url or ""
    if url.startswith("/certificate-files/"):
        filename = url.rsplit("/", 1)[-1]
        if filename:
            return filename
    return f"certificate_{uuid.uuid4().hex}.pdf"


def refresh_one(db, cert, base_url: str, dry_run: bool) -> None:
    # Fetch ONLY the display names via column-targeted queries. Loading full
    # User ORM objects (cert.student / course.instructor) would SELECT every
    # mapped column, including ones the live DB may lack (e.g. totp_secret on a
    # DB that predates that model change) — which would blow up here. We only
    # need names, so ask for just those columns.
    student_name = (
        db.query(User.display_name).filter(User.id == cert.user_id).scalar()
    )
    course_row = (
        db.query(Course.post_title, Course.post_author)
        .filter(Course.id == cert.course_id)
        .first()
    )
    course_title = course_row[0] if course_row else None
    instructor_name = None
    if course_row and course_row[1]:
        instructor_name = (
            db.query(User.display_name).filter(User.id == course_row[1]).scalar()
        )

    # 1) Drop rendered caches so the HTML view / HTML-PDF re-render with new QR.
    if not dry_run:
        CertificateService.clear_html_pdf_cache(cert)
        CertificateService.clear_png_cache(cert)

    # 2) Rebuild the ReportLab static PDF in place, same hash → same links.
    filename = _static_pdf_path(cert)
    file_path = os.path.join(CERT_DIR, filename)
    data = {
        "student_name": student_name or "Student",
        "course_title": course_title or "Course",
        "instructor_name": instructor_name or "SashaInfinity",
        "completion_date": cert.completion_date,
        "certificate_id": str(cert.id),
        "certificate_hash": cert.certificate_hash,
        "base_url": base_url,
    }

    if dry_run:
        print(
            f"  [dry-run] would rebuild {file_path} and clear caches for "
            f"cert id={cert.id} hash={cert.certificate_hash}"
        )
        return

    os.makedirs(CERT_DIR, exist_ok=True)
    CertificateService._generate_pdf(data, file_path)
    cert.certificate_download_url = f"/certificate-files/{filename}"
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing files or the DB.",
    )
    args = parser.parse_args()

    settings = get_settings()
    base_url = getattr(settings, "FRONTEND_URL", "https://lms.sashainfinity.com").rstrip("/")
    print(f"Public verification base URL: {base_url}")
    print(f"QR/link format: {base_url}/verify-certificate/<certificate_hash>\n")

    db = SessionLocal()
    ok = failed = 0
    try:
        certs = db.query(IssuedCertificate).order_by(IssuedCertificate.id).all()
        print(f"Found {len(certs)} issued certificate(s) to refresh.\n")
        for cert in certs:
            try:
                refresh_one(db, cert, base_url, args.dry_run)
                ok += 1
                print(f"✅ cert id={cert.id} (user={cert.user_id}, course={cert.course_id})")
            except Exception as e:  # noqa: BLE001 — best-effort per-cert
                db.rollback()
                failed += 1
                print(f"❌ cert id={cert.id} failed: {e}")
    finally:
        db.close()

    print(f"\nDone. Refreshed: {ok}, Failed: {failed}"
          f"{'  (dry-run — nothing written)' if args.dry_run else ''}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
