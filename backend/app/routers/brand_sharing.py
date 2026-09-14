from html import escape
import re
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import get_settings
from app.models.course import Course
from app.services.brand_artwork import render_banner

router = APIRouter()


def public_course(db, id):
    course = (
        db.query(Course)
        .filter(Course.id == id, Course.post_status.in_(["publish", "published"]))
        .first()
    )
    if not course:
        raise HTTPException(404, "Public course not found.")
    return course


def plain(value):
    return re.sub(r"<[^>]*>", " ", value or "").strip()[:250]


@router.get("/courses/{course_id}/image.png")
def course_image(course_id: int, db: Session = Depends(get_db)):
    course = public_course(db, course_id)
    return Response(
        render_banner(course.post_title[:250], plain(course.post_excerpt)),
        media_type="image/png",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/courses/{course_id}", response_class=HTMLResponse)
def course_share(course_id: int, db: Session = Depends(get_db)):
    course = public_course(db, course_id)
    base = get_settings().FRONTEND_URL.rstrip("/")
    url = base + "/courses/" + quote(course.post_name or str(course.id), safe="")
    image = base + f"/api/v1/share/courses/{course.id}/image.png"
    title = escape(course.post_title[:250])
    description = escape(
        plain(course.post_excerpt) or "A little curiosity. A world of possibility."
    )
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · SashaInfinity</title><meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:image" content="{escape(image,quote=True)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{escape(image,quote=True)}"><link rel="canonical" href="{escape(url,quote=True)}"></head><body style="margin:0;background:#fff4e6;color:#512d14;font-family:Arial;padding:5vw"><main style="max-width:900px;margin:auto"><img src="{escape(image,quote=True)}" alt="SashaInfinity course banner" style="width:100%;border-radius:24px"><h1>{title}</h1><p>{description}</p><a href="{escape(url,quote=True)}" style="display:inline-block;padding:16px 24px;border-radius:12px;background:linear-gradient(120deg,#ffd5a5,#ff9b54);color:#512d14">Explore this course →</a></main></body></html>""",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
