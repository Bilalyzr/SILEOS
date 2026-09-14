"""
Fix course slugs (post_name) in the database.
This script regenerates all course post_name values based on their titles.
"""
import sys
import unicodedata
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.course import Course

def slugify_title(title: str) -> str:
    """Build a URL-safe base slug from a course title."""
    if not title:
        return ""
    try:
        normalized = unicodedata.normalize("NFKD", title)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    except Exception:
        ascii_only = ""
    # Lowercase, replace spaces/non-alphanum with hyphens
    slug = ascii_only.lower()
    slug = "-".join(slug.split())  # spaces to hyphens
    # Remove non-alphanum except hyphens
    slug = "-".join(s for s in slug.split("-") if s)
    return slug

def fix_all_slugs():
    db: Session = SessionLocal()
    try:
        courses = db.query(Course).all()
        print(f"Found {len(courses)} courses to fix")

        for course in courses:
            old_slug = course.post_name
            # Generate new slug
            base = slugify_title(course.post_title or "")
            if not base:
                base = f"course-{course.id}"
            new_slug = f"{base}-{course.id}"

            # Update directly (bypass ensure_slug check)
            course.post_name = new_slug
            print(f"  Course {course.id}: '{course.post_title}'")
            print(f"    Old slug: {old_slug}")
            print(f"    New slug: {new_slug}")

        db.commit()
        print("Done! All course slugs updated.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_all_slugs()
