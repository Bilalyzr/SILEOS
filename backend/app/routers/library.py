"""Digital Library API (spec §4) — mounted at /api/v1/library.

redirect_slashes=False: every path here is declared WITHOUT a trailing
slash (create is @router.post("")), and '/library' must be added to
axios.ts's noSlashEndpoints — the gamification-404 lesson.

ROUTE ORDER MATTERS: fixed-path GETs (/mine, /me, /suggestions) are
declared BEFORE GET /{slug} so they never match as a slug, and the
int-typed /{ebook_id}/... routes are declared before it too. GET /{slug}
is the LAST GET in this file — it is the catch-all.

Caching (spec §4, Global Constraint 7): ONLY the two anonymous-safe public
reads (GET "" and GET /{slug}) call apply_public_cache, which stamps authed
responses `private, no-store` and always sets `Vary: Authorization`. It is
NEVER wired into /me, /mine, /sales, /download or /sample.

Range requests: deferred (spec §3 explicitly allows full-file streaming at
launch). FileResponse does honour Range for the static file it serves, but
no partial-content behaviour is contracted or tested here.

Ownership (spec §4): instructor endpoints are owner-scoped, admin-any —
mirrors games.py exactly. Students touch only the public store, /me,
claim, download and sample (Tasks 4/6/7).

Money: prices are whole rupees (price_inr); the payments router owns the
single paise boundary. file_path/sample_path NEVER appear in any response
body (spec §3) — _ebook_dict exposes has_file/has_sample booleans only.

Response style: plain dicts, no envelopes (matches games.py/h5p.py).
"""
import logging
import uuid
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, HTTPException, Query, Request,
                     Response, UploadFile, status)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StrictInt, validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache_headers import apply_public_cache
from app.core.database import get_db
from app.models.course import Course
from app.models.ebook import EBOOK_CATEGORIES, Ebook, EbookGrant, effective_price_inr
from app.models.payment import Order, OrderItem, OrderStatus
from app.models.user import User
from app.services import library_storage
from app.services.auth_service import AuthService
from app.services.course_service import _slugify_title

router = APIRouter()
logger = logging.getLogger(__name__)

# Cover images are rendered into other users' browsers as an <img src>. Only
# these schemes may ever reach one: a plain http(s) absolute URL or a
# site-relative /uploads/ path from the existing public uploads flow.
# Everything else — javascript:, data:, vbscript:, file:, and
# protocol-relative "//host/x" — is rejected at the API boundary (422).
_COVER_ALLOWED_PREFIXES = ("https://", "http://", "/uploads/")


def _validate_cover_image(v: "str | None") -> "str | None":
    if v is None:
        return v
    v = v.strip()
    if not v:
        return ""
    if v.startswith("//"):           # protocol-relative — inherits any scheme
        raise ValueError("cover_image must be an http(s) URL or an /uploads/ path")
    if not v.startswith(_COVER_ALLOWED_PREFIXES):
        raise ValueError("cover_image must be an http(s) URL or an /uploads/ path")
    return v


def _validate_title(v: "str | None") -> "str | None":
    """min_length runs BEFORE any strip, so "   " would otherwise sail through
    and be stored as "" — a titleless live product once published. Strip
    first, then require at least one real character."""
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("title must not be blank")
    return v


# ---- request schemas ---------------------------------------------------------

class EbookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    category: str
    # StrictInt: a bool is an int in Python and "299"/1.5 coerce silently —
    # money fields must never be guessed at.
    price_inr: StrictInt = Field(..., ge=0, le=1_000_000)   # whole rupees
    discount_price_inr: Optional[StrictInt] = Field(None, ge=0)
    cover_image: str = Field("", max_length=500)      # existing public uploads flow
    page_count: Optional[StrictInt] = Field(None, ge=1, le=100_000)
    concept_tags: List[str] = Field(default_factory=list, max_items=10)
    course_id: Optional[int] = None

    @validator("title")
    def _title_not_blank(cls, v):
        return _validate_title(v)

    @validator("cover_image")
    def _cover_scheme(cls, v):
        return _validate_cover_image(v)

    @validator("category")
    def _category_in_enum(cls, v):
        if v not in EBOOK_CATEGORIES:
            raise ValueError(f"category must be one of {list(EBOOK_CATEGORIES)}")
        return v

    @validator("concept_tags", each_item=True)
    def _tag_caps(cls, v):
        v = str(v).strip()
        if not (1 <= len(v) <= 50):
            raise ValueError("each concept tag must be 1..50 chars")
        return v

    @validator("discount_price_inr")
    def _discount_below_price(cls, v, values):
        price = values.get("price_inr")
        if v is not None and price is not None and v >= price:
            raise ValueError("discount_price_inr must be less than price_inr")
        return v


class EbookUpdate(EbookCreate):
    """PUT body — same fields/caps, everything optional. The cross-field
    discount<price rule is re-checked against the MERGED row in the handler
    (a kept discount must still undercut a newly-lowered price)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    price_inr: Optional[StrictInt] = Field(None, ge=0, le=1_000_000)

    @validator("title")
    def _title_not_blank(cls, v):
        """A PUT that blanks the title of a PUBLISHED ebook is the worst case
        (a titleless live product), so the same strip-then-require rule
        applies here, not just at create."""
        return _validate_title(v)

    @validator("cover_image")
    def _cover_scheme(cls, v):
        return _validate_cover_image(v)

    @validator("category")
    def _category_in_enum(cls, v):
        if v is not None and v not in EBOOK_CATEGORIES:
            raise ValueError(f"category must be one of {list(EBOOK_CATEGORIES)}")
        return v


# ---- helpers -----------------------------------------------------------------

def _get_ebook_or_404(db: Session, ebook_id: int) -> Ebook:
    ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()
    if not ebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Ebook not found")
    return ebook


def _require_owner_or_admin(ebook: Ebook, current_user: User) -> None:
    if ebook.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized for this ebook")


def _is_privileged(ebook: Ebook, user: "User | None") -> bool:
    return user is not None and (user.id == ebook.owner_id or user.role == "admin")


def _build_ebook_slug(db: Session, ebook: Ebook) -> str:
    """`<title-slug>-<id>` like course slugs (course_service.build_default_slug);
    `ebook-<id>` for pure-Tamil titles.

    The embedded id makes a collision very unlikely but NOT impossible — a
    title that already ends in a number ("Volume 7") can derive a slug another
    row legitimately holds, and Ebook.slug is UNIQUE, so a naive build turns
    that into an IntegrityError 500. Dedupe the way course_service.
    generate_unique_slug does: append -2, -3, ... until the slug is free
    (excluding this ebook's own row, so a no-op re-slug keeps its slug)."""
    base = _slugify_title(ebook.title or "")
    root = f"{base}-{ebook.id}" if base else f"ebook-{ebook.id}"

    candidate, n = root, 2
    while True:
        taken = (db.query(Ebook.id)
                 .filter(Ebook.slug == candidate, Ebook.id != ebook.id)
                 .first())
        if taken is None:
            return candidate
        candidate = f"{root}-{n}"
        n += 1
        if n > 10000:                      # safety valve, matches course_service
            return f"{root}-{uuid.uuid4().hex[:8]}"


def _ebook_dict(ebook: Ebook, *, owned: "bool | None" = None,
                 course_title: "str | None" = None) -> dict:
    """Public/instructor shape. file_path/sample_path are PRIVATE and never
    leave the server — only has_file/has_sample booleans do."""
    d = {
        "id": ebook.id,
        "owner_id": ebook.owner_id,
        "slug": ebook.slug,
        "title": ebook.title,
        "description": ebook.description or "",
        "category": ebook.category,
        "price_inr": int(ebook.price_inr or 0),
        "discount_price_inr": ebook.discount_price_inr,
        "effective_price_inr": effective_price_inr(ebook),
        "cover_image": ebook.cover_image or "",
        "page_count": ebook.page_count,
        "concept_tags": list(ebook.concept_tags or []),
        "course_id": ebook.course_id,
        "course_title": course_title,
        "status": ebook.status,
        "has_file": bool(ebook.file_path),
        "has_sample": bool(ebook.sample_path),
        "file_size_bytes": int(ebook.file_size_bytes or 0),
        "created_at": ebook.created_at,
        "updated_at": ebook.updated_at,
    }
    if owned is not None:
        d["owned"] = owned
    return d


def _course_titles(db: Session, ebooks: "list[Ebook]") -> dict:
    ids = {e.course_id for e in ebooks if e.course_id}
    if not ids:
        return {}
    return {c.id: c.post_title for c in
            db.query(Course).filter(Course.id.in_(ids)).all()}


# ---- instructor/admin endpoints (owner-scoped, admin-any) ---------------------

@router.post("")
async def create_ebook(
    payload: EbookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Create a draft (metadata only — files arrive via /file and /sample)."""
    ebook = Ebook(
        owner_id=current_user.id,
        title=payload.title.strip(),
        slug="pending",
        description=payload.description,
        category=payload.category,
        price_inr=payload.price_inr,
        discount_price_inr=payload.discount_price_inr,
        cover_image=payload.cover_image,
        page_count=payload.page_count,
        concept_tags=payload.concept_tags,
        course_id=payload.course_id,
        status="draft",
    )
    db.add(ebook)
    db.flush()                      # assign id, then derive the slug from it
    ebook.slug = _build_ebook_slug(db, ebook)
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.get("/mine")
async def list_my_ebooks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Owner's ebooks (admin sees all), paginated — a prolific instructor's
    library must not become an unbounded response. `count` is the page size,
    `total` the unpaginated row count."""
    query = db.query(Ebook)
    if current_user.role != "admin":
        query = query.filter(Ebook.owner_id == current_user.id)
    total = query.count()
    ebooks = (query.order_by(Ebook.updated_at.desc())
              .offset(offset).limit(limit).all())
    titles = _course_titles(db, ebooks)
    return {"ebooks": [_ebook_dict(e, course_title=titles.get(e.course_id))
                        for e in ebooks],
            "count": len(ebooks),
            "total": total,
            "limit": limit,
            "offset": offset}


# ---- public store (anon-edge-cacheable; spec §4) -----------------------------

@router.get("")
async def list_published_ebooks(
    request: Request,
    response: Response,
    category: Optional[str] = None,
    q: Optional[str] = None,
    course_id: Optional[int] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Published ebooks with store filters. Anon requests are edge-cacheable;
    the helper stamps authed ones `private, no-store` (the body is identical
    for every caller — no per-user data here, and drafts are hidden even from
    their own owner: /mine is the owner's view)."""
    apply_public_cache(request, response, s_maxage=300, swr=600)
    query = db.query(Ebook).filter(Ebook.status == "published")
    if category:
        query = query.filter(Ebook.category == category)
    if q:
        query = query.filter(Ebook.title.ilike(f"%{q.strip()}%"))
    if course_id:
        query = query.filter(Ebook.course_id == course_id)
    ebooks = query.order_by(Ebook.created_at.desc()).all()
    if tag:
        # JSON containment isn't portable across SQLite/Postgres — filter in
        # Python; the published set is small (a store, not a firehose).
        wanted = tag.strip().lower()
        ebooks = [e for e in ebooks
                  if wanted in [str(t).lower() for t in (e.concept_tags or [])]]
    titles = _course_titles(db, ebooks)
    return {"ebooks": [_ebook_dict(e, course_title=titles.get(e.course_id))
                       for e in ebooks],
            "count": len(ebooks)}


@router.get("/me")
async def my_library(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """My grants with download availability. Per-user — NEVER edge-cached
    (no apply_public_cache here, Global Constraint 7). Unpublished ebooks the
    user was granted stay listed: a grant survives unpublish (spec §4)."""
    grants = (db.query(EbookGrant)
              .filter(EbookGrant.user_id == current_user.id)
              .order_by(EbookGrant.granted_at.desc())
              .all())
    ebooks_by_id = {e.id: e for e in db.query(Ebook).filter(
        Ebook.id.in_([g.ebook_id for g in grants])).all()} if grants else {}
    items = []
    for g in grants:
        ebook = ebooks_by_id.get(g.ebook_id)
        if ebook is None:
            continue
        d = _ebook_dict(ebook)
        d["granted_at"] = g.granted_at
        d["downloadable"] = bool(ebook.file_path)
        items.append(d)
    return {"items": items, "count": len(items)}


@router.put("/{ebook_id}")
async def update_ebook(
    ebook_id: int,
    payload: EbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)

    data = payload.dict(exclude_unset=True)
    for field in ("title", "description", "category", "price_inr",
                  "discount_price_inr", "cover_image", "page_count",
                  "concept_tags", "course_id"):
        if field in data:
            setattr(ebook, field,
                    data[field].strip() if field == "title" else data[field])
    # Cross-field rule re-checked against the MERGED row.
    if ebook.discount_price_inr is not None and \
            ebook.discount_price_inr >= int(ebook.price_inr or 0):
        raise HTTPException(status_code=422,
                             detail="discount_price_inr must be less than price_inr")
    if "title" in data:
        ebook.slug = _build_ebook_slug(db, ebook)
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/file")
async def upload_ebook_file(
    ebook_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Upload/replace the sellable file. Stored under the EBOOK OWNER's dir
    (admin uploads land in the owner's 5GB quota, not the admin's)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    rel_path, size = library_storage.save_ebook_file(ebook.owner_id, file, db)
    old = ebook.file_path
    ebook.file_path = rel_path
    ebook.file_size_bytes = size
    try:
        db.commit()
    except Exception:
        db.rollback()
        library_storage.delete_stored_file(rel_path)  # never orphan the new blob
        raise
    db.refresh(ebook)
    if old:
        library_storage.delete_stored_file(old)  # after commit: never orphan the live row
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/sample")
async def upload_ebook_sample(
    ebook_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Upload/replace the free-preview sample. PDF only (spec §1)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    rel_path, _size = library_storage.save_ebook_file(
        ebook.owner_id, file, db, allowed={"pdf"})
    old = ebook.sample_path
    ebook.sample_path = rel_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        library_storage.delete_stored_file(rel_path)  # never orphan the new blob
        raise
    db.refresh(ebook)
    if old:
        library_storage.delete_stored_file(old)
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/claim")
async def claim_free_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Claim a FREE published ebook (the endpoint payments/create-order
    points free ebooks at). Paid ebooks 422 here — they must go through
    create-order so the money trail is never bypassed. Idempotent: an
    existing grant is a 200 no-op (UNIQUE(ebook_id, user_id) backs the
    race); owners/admins already have access and simply get their row.
    """
    ebook = _get_ebook_or_404(db, ebook_id)
    if not _is_privileged(ebook, current_user):
        if ebook.status != "published":
            # Same doctrine as download: unpublished inventory is
            # indistinguishable from nonexistent to non-owners.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Ebook not found")
        if effective_price_inr(ebook) != 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This ebook is paid — purchase it via checkout")
    from app.services.fulfillment_service import grant_ebook
    created = grant_ebook(db, ebook_id=ebook.id, user_id=current_user.id,
                          order_id=None, source="free_claim")
    db.commit()
    db.refresh(ebook)
    d = _ebook_dict(ebook, owned=True)
    d["newly_granted"] = created
    return d


@router.post("/{ebook_id}/publish")
async def publish_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Publish requires the sellable file to be present (spec §4)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    if not ebook.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Cannot publish: upload the ebook file first")
    if not ebook.title or not ebook.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Cannot publish: title is required")
    if ebook.price_inr is None or int(ebook.price_inr) < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Cannot publish: a valid price is required")
    ebook.status = "published"
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/unpublish")
async def unpublish_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Allowed anytime. Only hides the ebook from the store — grants keep
    working (the download gate checks grants, not status; spec §4)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    ebook.status = "draft"
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.delete("/{ebook_id}")
async def delete_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """409 while ANY grant exists — sold content is never deleted (spec §4).
    Unpublish is the way to retire a sold ebook.

    Also 409 while any order line still references the ebook even when no
    grant survives (a refund removes the grant but leaves the money trail):
    deleting the row would dangle OrderItem.ebook_id / Order.ebook_id and
    break every revenue report that joins through them."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    grant_count = db.query(func.count(EbookGrant.id)).filter(
        EbookGrant.ebook_id == ebook.id).scalar() or 0
    if grant_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {grant_count} student(s) own this ebook. "
                   "Unpublish it instead — sold content is never deleted.")
    order_refs = (db.query(func.count(OrderItem.id))
                  .filter(OrderItem.ebook_id == ebook.id).scalar() or 0)
    order_refs += (db.query(func.count(Order.id))
                   .filter(Order.ebook_id == ebook.id).scalar() or 0)
    if order_refs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete: this ebook appears on existing orders. "
                   "Unpublish it instead — the money trail is never broken.")
    file_path, sample_path = ebook.file_path, ebook.sample_path
    db.delete(ebook)
    db.commit()
    library_storage.delete_stored_file(file_path)
    library_storage.delete_stored_file(sample_path)
    return {"success": True, "id": ebook_id}


@router.get("/{ebook_id}/sales")
async def ebook_sales(
    ebook_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Owner sales panel: grant count, REALISED gross, last sale, buyers by
    display_name ONLY — never emails (spec §4). `buyers` is paginated;
    `count` stays the full grant total so the panel's headline number is
    never a page size."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    grant_query = (db.query(EbookGrant)
                   .filter(EbookGrant.ebook_id == ebook.id)
                   .order_by(EbookGrant.granted_at.desc()))
    total_grants = grant_query.count()
    last_sale = grant_query.first()
    grants = grant_query.offset(offset).limit(limit).all()

    # Revenue must be REALISED money only. Summing OrderItem.total on its own
    # credits refunded, cancelled, pending and failed orders as income; mock
    # orders (test/dev payments) are not income either. Join Order and filter
    # exactly the way dashboard.py's course-revenue query does — one canonical
    # definition of "this actually earned money" across the codebase.
    gross = (db.query(func.coalesce(func.sum(OrderItem.total), 0))
             .select_from(OrderItem)
             .join(Order, OrderItem.order_id == Order.id)
             .filter(OrderItem.ebook_id == ebook.id,
                     Order.order_status == OrderStatus.COMPLETED,
                     func.coalesce(Order.payment_method, "") != "mock")
             .scalar())
    users_by_id = {u.id: u for u in db.query(User).filter(
        User.id.in_([g.user_id for g in grants])).all()} if grants else {}
    return {
        "ebook_id": ebook.id,
        "count": total_grants,
        "gross_inr": float(gross or 0),
        "last_sale_at": last_sale.granted_at if last_sale else None,
        "buyers": [{
            "display_name": users_by_id[g.user_id].display_name
            if g.user_id in users_by_id else "Unknown",
            "source": g.source,
            "granted_at": g.granted_at,
        } for g in grants],
        "limit": limit,
        "offset": offset,
    }


# ---- streaming gates (spec §3: never a redirect to a static path) ------------
#
# THE PAID-CONTENT ACCESS BOUNDARY. Both routes stream from the app with
# FileResponse; neither ever emits a public cache header, echoes a stored
# path, or hands out a URL under /uploads. Paths are ALWAYS resolved by
# library_storage.resolve_ebook_path (normalize-and-reassert inside the
# ebooks root, 404 on a missing/escaping path) — never built here.
# Range requests are deferred (spec §3 permits full-file streaming at
# launch); no partial-content behaviour is contracted.

@router.get("/{ebook_id}/download")
async def download_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Grant-gated download. Owner/admin need no grant. A granted student
    keeps access after unpublish (the gate checks the grant, not status).
    Drafts 404 to everyone else so unpublished inventory can't be probed."""
    ebook = _get_ebook_or_404(db, ebook_id)
    if not _is_privileged(ebook, current_user):
        grant = db.query(EbookGrant).filter(
            EbookGrant.ebook_id == ebook.id,
            EbookGrant.user_id == current_user.id).first()
        if grant is None:
            if ebook.status != "published":
                # Draft + no grant: indistinguishable from "doesn't exist".
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Ebook not found")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not own this ebook")
    if not ebook.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No file uploaded for this ebook")
    # resolve_ebook_path 404s (never 500s) on a path that escaped the root or
    # whose blob is gone from disk.
    path = library_storage.resolve_ebook_path(ebook.file_path)
    ext = path.suffix.lstrip(".").lower()
    return FileResponse(
        path,
        media_type=library_storage.MEDIA_TYPES.get(ext, "application/octet-stream"),
        # The download filename is the sanitized slug, NEVER the stored uuid
        # name or the on-disk path (spec §3).
        filename=f"{ebook.slug}.{ext}",   # → Content-Disposition: attachment
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{ebook_id}/sample")
async def download_sample(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """Grant-free preview (semi-public by design, spec §3): published samples
    stream to anyone, authenticated or not; drafts only to owner/admin. Still
    app-streamed and never edge-cached — never nginx-static."""
    ebook = _get_ebook_or_404(db, ebook_id)
    if ebook.status != "published" and not _is_privileged(ebook, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ebook not found")
    if not ebook.sample_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No sample available for this ebook")
    path = library_storage.resolve_ebook_path(ebook.sample_path)
    return FileResponse(path, media_type="application/pdf",
                        filename=f"{ebook.slug}-sample.pdf",
                        headers={"Cache-Control": "private, no-store"})


# ---- public detail — LAST GET in the file: /{slug} is the catch-all ----------

@router.get("/{slug}")
async def get_ebook_detail(
    slug: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """Published detail. `owned` appears ONLY for authed users — whose
    responses apply_public_cache already stamps `private, no-store`, so the
    per-user flag can never leak through a shared edge (spec §4). The slug
    lookup is an EXACT equality match (no LIKE, no path semantics), so a
    traversal-shaped slug is simply a slug that doesn't exist."""
    apply_public_cache(request, response, s_maxage=60, swr=600)
    ebook = db.query(Ebook).filter(Ebook.slug == slug,
                                   Ebook.status == "published").first()
    if not ebook:
        # Drafts are indistinguishable from nonexistent ebooks here, for
        # every caller including the owner (who uses /mine instead).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ebook not found")
    titles = _course_titles(db, [ebook])
    owned = None
    if current_user is not None:
        owned = _is_privileged(ebook, current_user) or db.query(EbookGrant).filter(
            EbookGrant.ebook_id == ebook.id,
            EbookGrant.user_id == current_user.id).first() is not None
    return _ebook_dict(ebook, owned=owned,
                       course_title=titles.get(ebook.course_id))
