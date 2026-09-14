"""
Clean up broken upload references in the database.

Run when the DB has rows pointing at files that no longer exist on disk
(typical after a volume remount, a botched migration, or legacy WP rows
referencing files that were never copied into the new uploads dir).

What it does:
  * Scans every Course.course_thumbnail and every UserProfile.profile_photo.
  * For each value shaped like /uploads/..., checks the corresponding file
    under UPLOAD_DIR.
  * If the file is missing, nulls the column so the UI falls back to the
    placeholder instead of triggering a broken-image 404 round-trip.

This script is idempotent — running it twice in a row is fine. It never
touches URLs that aren't /uploads/* (e.g. https://cloudinary.com/...).

Usage (from the repo root):
    docker compose exec -T backend python -m app.scripts.cleanup_broken_uploads
Or with `--dry-run` to just print the findings without writing:
    docker compose exec -T backend python -m app.scripts.cleanup_broken_uploads --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.course import Course
from app.models.user import UserProfile


def _is_broken_upload_url(upload_dir: Path, url: str) -> bool:
    """Return True if url looks like /uploads/... but the file is missing."""
    if not url or not url.startswith("/uploads/"):
        return False
    # /uploads/images/X.jpg  →  images/X.jpg
    rel = url.lstrip("/").replace("uploads/", "", 1)
    return not (upload_dir / rel).exists()


def cleanup(dry_run: bool = False) -> int:
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        print(f"UPLOAD_DIR {upload_dir} does not exist — refusing to run (would flag everything).")
        return 2

    db = SessionLocal()
    try:
        bad_courses = [
            c for c in db.query(Course).all()
            if _is_broken_upload_url(upload_dir, c.course_thumbnail or "")
        ]
        print(f"Courses with broken thumbnails: {len(bad_courses)}")
        for c in bad_courses:
            print(f"  id={c.id} title={c.post_title!r} -> {c.course_thumbnail}")
            if not dry_run:
                c.course_thumbnail = ""

        bad_profiles = [
            p for p in db.query(UserProfile).all()
            if _is_broken_upload_url(upload_dir, p.profile_photo or "")
        ]
        print(f"Profiles with broken photos: {len(bad_profiles)}")
        for p in bad_profiles:
            print(f"  user_id={p.user_id} -> {p.profile_photo}")
            if not dry_run:
                p.profile_photo = ""

        if dry_run:
            print("Dry run — no writes.")
            return 0

        db.commit()
        print(f"Cleared {len(bad_courses)} course thumbnails and {len(bad_profiles)} profile photos.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only print findings; don't write.")
    args = parser.parse_args()
    sys.exit(cleanup(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
