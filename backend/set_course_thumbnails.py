"""
One-time script: set `course_thumbnail` for the four official courses to the
bundled 16:9 artwork served from the frontend at `/course-thumbnails/...`.

Matching mirrors the frontend `getLocalCourseThumbnail()` helper so the DB and
the UI agree. Safe to re-run (idempotent) and a no-op for courses that don't
match. Run with Postgres up:

    docker-compose exec backend python set_course_thumbnails.py
    # or, from backend/ with the app env: python set_course_thumbnails.py
"""
import re

from app.core.database import SessionLocal
from app.models.course import Course


def pick_thumbnail(title: str) -> str:
    """Return the public thumbnail path for a course title, or '' if none."""
    if not title:
        return ""
    t = title.lower()
    has_full_stack = bool(re.search(r"full[\s-]*stack", t))
    # Both live full-stack courses carry "AI" in the title, so the advanced one
    # has to be split off first or it would take the other course's artwork.
    is_advanced = bool(re.search(r"advance", t))

    if has_full_stack and is_advanced:
        return "/course-thumbnails/full-stack-development.png"
    if has_full_stack:
        return "/course-thumbnails/full-stack-web-development-ai.png"
    if "excel" in t or "data analytics" in t:
        return "/course-thumbnails/data-analytics-excel-beginner.png"
    if "react" in t and "native" not in t:
        return "/course-thumbnails/react-js-mastery.png"
    return ""


def main() -> None:
    db = SessionLocal()
    updated = 0
    try:
        for course in db.query(Course).all():
            thumb = pick_thumbnail(course.post_title or "")
            if thumb and course.course_thumbnail != thumb:
                print(f"  [{course.id}] {course.post_title!r} -> {thumb}")
                course.course_thumbnail = thumb
                updated += 1
        db.commit()
        print(f"Done. Updated {updated} course(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
