"""Public bundle catalog endpoints.

Bundle contents shown here are always resolved live against the current
Course rows (published + paid only) — this is a *catalog* view, distinct
from the immutable order-notes snapshot fulfillment reads at purchase time
(see app/models/bundle.py).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.cache_headers import apply_public_cache
from app.core.database import get_db
from app.models.bundle import Bundle, BundleCourse
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.bundle import BundleCourseOut, BundleDetailOut, BundleOut
from app.services.auth_service import AuthService
from app.services.membership_access import PUBLISHED_STATUSES

router = APIRouter()


def _bundle_out(db: Session, bundle: Bundle) -> BundleOut:
    """Build the public course list for a bundle from currently published,
    paid courses only — a course pulled from sale or unpublished after the
    bundle was created silently drops out of the catalog view (fulfillment
    is unaffected; it reads the order-notes snapshot)."""
    rows = (
        db.query(Course)
        .join(BundleCourse, BundleCourse.course_id == Course.id)
        .filter(
            BundleCourse.bundle_id == bundle.id,
            Course.course_price_type == "paid",
            Course.post_status.in_(PUBLISHED_STATUSES),
        )
        .all()
    )
    courses = [
        BundleCourseOut(id=c.id, title=c.post_title, price=float(c.course_price or 0))
        for c in rows
    ]
    combined_price = sum(c.price for c in courses)
    return BundleOut(
        id=bundle.id,
        slug=bundle.slug,
        name=bundle.name,
        description=bundle.description or "",
        bundle_price=float(bundle.bundle_price),
        combined_price=combined_price,
        courses=courses,
    )


@router.get("", response_model=list[BundleOut])
def list_bundles(request: Request, response: Response, db: Session = Depends(get_db)):
    apply_public_cache(request, response, s_maxage=300, swr=600)
    bundles = (
        db.query(Bundle)
        .filter(Bundle.is_active.is_(True))
        .order_by(Bundle.created_at.desc())
        .all()
    )
    return [_bundle_out(db, b) for b in bundles]


@router.get("/{slug}", response_model=BundleDetailOut)
def get_bundle(
    slug: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    apply_public_cache(request, response, s_maxage=60, swr=600)
    bundle = (
        db.query(Bundle)
        .filter(Bundle.slug == slug, Bundle.is_active.is_(True))
        .first()
    )
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    out = _bundle_out(db, bundle)
    owned_course_ids: list[int] = []
    if current_user is not None:
        course_ids = [c.id for c in out.courses]
        if course_ids:
            owned_course_ids = [
                r[0]
                for r in db.query(Enrollment.course_id)
                .filter(
                    Enrollment.user_id == current_user.id,
                    Enrollment.course_id.in_(course_ids),
                    # Only live access counts as "owned". A suspended
                    # membership row is exactly what a buyer can (and should)
                    # still pay to restore, so the badge must not claim it —
                    # this matches create-order's already-own guard.
                    Enrollment.enrollment_status == "enrolled",
                )
                .distinct()
                .all()
            ]
    return BundleDetailOut(**out.model_dump(), owned_course_ids=owned_course_ids)
