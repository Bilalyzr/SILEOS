#!/usr/bin/env python3
"""
Seed the four additional certificate templates into the `certificates` table.

Each row's `post_name` (slug) names an HTML file under
`certificates/templates/<slug>.html` that the render pipeline
(`resolve_template_path` in app/routers/certificates.py) loads per-course.

The existing default design (`certificates/template.html`) stays the fallback
and is exposed here as the "Certificate of Excellence" row (id 1) so it shows
up in the instructor's template picker alongside the new designs.

Idempotent: matches on `post_name`, updating the row if it already exists and
inserting it otherwise. Safe to run repeatedly.

Usage (inside the backend container, or anywhere the DB is reachable):

    docker-compose exec backend python seed_certificate_templates.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User
from app.models.certificate import Certificate


# slug -> display metadata. The slug MUST equal the template filename stem
# in certificates/templates/<slug>.html.
TEMPLATES = [
    {
        "slug": "sasha-3d",
        "title": "Sasha 3D Celebration",
        "excerpt": "Playful mild-orange design featuring the 3D Sasha mascot.",
        "bg_color": "#fdfaf5", "title_color": "#0b2444", "font": "Playfair Display",
    },
    {
        "slug": "royal-navy",
        "title": "Royal Navy",
        "excerpt": "Formal navy-and-gold classic diploma with an ornate frame.",
        "bg_color": "#fcf8ef", "title_color": "#061e43", "font": "Playfair Display",
    },
    {
        "slug": "modern-minimal",
        "title": "Modern Minimal",
        "excerpt": "Clean, contemporary layout with a single orange accent.",
        "bg_color": "#ffffff", "title_color": "#141b26", "font": "Space Grotesk",
    },
    {
        "slug": "aurora-gradient",
        "title": "Aurora Gradient",
        "excerpt": "Vibrant orange-to-navy hero gradient with a modern glass panel.",
        "bg_color": "#ffffff", "title_color": "#061e43", "font": "Sora",
    },
]


def _resolve_author(db: Session) -> int:
    """post_author is a NOT NULL FK to users.id — pick an admin, else any user."""
    user = (
        db.query(User).filter(User.role == "admin").order_by(User.id).first()
        or db.query(User).order_by(User.id).first()
    )
    if not user:
        raise SystemExit("❌ No users exist yet — create an admin first (see create_admin.py).")
    return user.id


def _ensure_default_row(db: Session, author_id: int) -> None:
    """Make sure the original design (template.html) is a selectable row.

    It keeps an EMPTY post_name so `resolve_template_path` falls back to the
    default template.html for it.
    """
    default = db.query(Certificate).filter(Certificate.id == 1).first()
    if default:
        if not (default.post_title or "").strip():
            default.post_title = "Certificate of Excellence"
        default.post_status = "publish"
        print(f"  ✓ default template row id=1 ('{default.post_title}') present")
        return
    row = Certificate(
        post_author=author_id,
        post_title="Certificate of Excellence",
        post_name="",  # empty slug -> default template.html
        post_excerpt="The classic SashaInfinity certificate design.",
        post_status="publish",
        post_type="tutor_certificates",
        certificate_orientation="landscape",
        background_color="#faf9f5",
        title_font_color="#0b2444",
        title_font_family="Playfair Display",
        body_font_family="Poppins",
        post_content="",
    )
    db.add(row)
    print("  + created default template row ('Certificate of Excellence')")


def seed(db: Session) -> None:
    author_id = _resolve_author(db)
    _ensure_default_row(db, author_id)

    for t in TEMPLATES:
        row = db.query(Certificate).filter(Certificate.post_name == t["slug"]).first()
        if row:
            row.post_title = t["title"]
            row.post_excerpt = t["excerpt"]
            row.post_status = "publish"
            row.post_type = "tutor_certificates"
            row.certificate_orientation = "landscape"
            row.background_color = t["bg_color"]
            row.title_font_color = t["title_color"]
            row.title_font_family = t["font"]
            row.body_font_family = "Poppins"
            print(f"  ✓ updated '{t['title']}' (slug={t['slug']}, id={row.id})")
        else:
            row = Certificate(
                post_author=author_id,
                post_title=t["title"],
                post_name=t["slug"],
                post_excerpt=t["excerpt"],
                post_status="publish",
                post_type="tutor_certificates",
                certificate_orientation="landscape",
                background_color=t["bg_color"],
                title_font_color=t["title_color"],
                title_font_family=t["font"],
                body_font_family="Poppins",
                post_content="",
            )
            db.add(row)
            print(f"  + created '{t['title']}' (slug={t['slug']})")

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        print("Seeding certificate templates…")
        seed(db)
        print("✅ Done. Templates available via GET /api/v1/certificates/templates/list")
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
