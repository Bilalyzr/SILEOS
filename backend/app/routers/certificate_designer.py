"""Instructor certificate designer API (Task 6 of the Learning Experience
plan, spec section C item 3).

Mounted at /api/v1/certificates/designer. Gives instructors CRUD over their
OWN elements_config-based Certificate templates (scoped by post_author),
admin sees/edits all, and a template an admin marks `is_global` becomes
readable (not editable) by every instructor.

This is deliberately a NEW, separate router from the legacy primitive
instructor `/templates/` CRUD in routers/certificates.py (superseded per
spec — that router stays for compat, unmodified, and is documented as
deprecated there) and from the admin-only `/certificate-templates-v2` CRUD
in routers/admin.py (also unmodified — this module does not touch it).
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.certificate import Certificate, IssuedCertificate
from app.models.course import Course
from app.models.user import User
from app.schemas.certificate import (
    DESIGNER_ELEMENT_TYPES,
    DESIGNER_MAX_ELEMENTS,
    DesignerPreviewRequest,
    DesignerTemplateCreate,
    DesignerTemplateOut,
    DesignerTemplateUpdate,
)
from app.services.auth_service import AuthService
from app.services.certificate_html_renderer import (
    CURATED_FONTS,
    is_safe_asset_src,
    sample_values,
    validate_border,
    validate_color,
    validate_font_weight,
    validate_letter_spacing,
)
from app.services.certificate_service import CertificateService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# elements_config validation (plan Task 6 binding: "validate elements_config
# shape — list of dicts, known types, numeric bounds, max 100 elements, fonts
# from the curated list else fallback font").
# ---------------------------------------------------------------------------

_NUMERIC_BOUND = 20000  # px — generous ceiling; certificates aren't billboard-sized


def _validate_numeric(el: Dict[str, Any], key: str, *, required: bool = False) -> None:
    if key not in el:
        if required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Element missing required field '{key}'",
            )
        return
    value = el[key]
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Element field '{key}' must be numeric",
        )
    if not (-_NUMERIC_BOUND <= float(value) <= _NUMERIC_BOUND):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Element field '{key}' out of bounds",
        )


_TEXT_ALIGNS = {"left", "center", "right"}
_SRC_FIELDS = ("image_url", "src")
_COLOR_FIELDS = ("font_color", "background_color", "fill", "line_color")


def validate_elements_config(elements: Any) -> List[Dict[str, Any]]:
    """Validate + normalize an elements_config payload. Raises
    HTTPException(422) on any structural problem (including an unsafe image
    source — rejected outright at write time, per fix-round H-1). Returns
    the normalized list, safe to store AND safe to render as-is.

    Rules (plan Task 6 binding + fix-round hardening):
      - must be a list of dicts
      - at most DESIGNER_MAX_ELEMENTS entries
      - `type` must be one of the known element types
      - x/y/width/height/rotation/z_index must be numeric and within bounds
      - font_family must be from the curated list, else silently corrected
        to the renderer's fallback font (never a hard rejection — an
        instructor pasting a design from elsewhere shouldn't lose their
        whole layout over one font name)
      - image_url/src (image, signature_image) must be a same-origin static
        path (/uploads/..., /certificate-files/...) or a data:image/...
        base64 URI — file://, blob:, and external http(s) are REJECTED here
        (H-1: this module renders via a headless Chrome navigated with
        --no-sandbox to a local file://, so an unconstrained src is a
        server-side SSRF/LFI primitive, not just a client-side one)
      - font_color/background_color/fill/line_color must be a hex/rgb(a)/
        short keyword color, else dropped to None (H-2: CSS-context
        injection via `;background:url(...)` etc. is not stoppable by
        HTML-escaping alone — an allowlist makes it impossible instead)
      - font_weight normalized to normal|bold|100-900
      - text_align normalized to left|center|right
      - letter_spacing normalized to a plain px value or dropped
      - border decomposed+re-validated (width/style/color) or dropped
    """
    if not isinstance(elements, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elements_config must be a list",
        )
    if len(elements) > DESIGNER_MAX_ELEMENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"elements_config exceeds the {DESIGNER_MAX_ELEMENTS}-element limit",
        )

    normalized: List[Dict[str, Any]] = []
    for idx, el in enumerate(elements):
        if not isinstance(el, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Element at index {idx} must be an object",
            )
        etype = el.get("type")
        if etype not in DESIGNER_ELEMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Element at index {idx} has unknown type '{etype}'",
            )
        for key in ("x", "y", "width", "height"):
            _validate_numeric(el, key)
        for key in ("rotation", "z_index", "font_size", "line_thickness", "border_radius"):
            _validate_numeric(el, key)
        # letter_spacing is NOT strict-numeric-or-422 here — it goes through
        # validate_letter_spacing() below, which tolerantly normalizes a
        # numeric value to "{x}px" and drops (rather than 422s) anything
        # that doesn't parse as one, consistent with how every other
        # CSS-context field in this function degrades instead of rejecting.

        el = dict(el)  # don't mutate the caller's object

        font = (el.get("font_family") or "").strip()
        if font and font not in CURATED_FONTS:
            el["font_family"] = None  # renderer falls back to its default stack

        # H-1: reject an unsafe image source outright at write time (an
        # instructor's own upload, not an arbitrary attacker payload, so a
        # hard rejection here — unlike the font fallback — is the right
        # trade-off: it surfaces the mistake immediately instead of silently
        # dropping the element later at render time).
        for key in _SRC_FIELDS:
            if el.get(key) and not is_safe_asset_src(el.get(key)):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Element at index {idx} field '{key}' must be an "
                        "uploaded asset path (/uploads/... or "
                        "/certificate-files/...) or a data:image/... URI"
                    ),
                )

        # H-2: colors/weight/align/letter-spacing/border are normalized
        # through the renderer's own allowlist validators so what gets
        # stored is byte-for-byte what render time would also accept —
        # never a raw pass-through of attacker-controllable CSS text.
        for key in _COLOR_FIELDS:
            if key in el:
                el[key] = validate_color(el.get(key))
        if "font_weight" in el:
            el["font_weight"] = validate_font_weight(el.get("font_weight"))
        if "text_align" in el:
            align = str(el.get("text_align") or "left").strip().lower()
            el["text_align"] = align if align in _TEXT_ALIGNS else "left"
        if "letter_spacing" in el:
            spacing = validate_letter_spacing(el.get("letter_spacing"))
            el["letter_spacing"] = float(spacing[:-2]) if spacing else None
        if "border" in el and el.get("border"):
            normalized_border = validate_border(el.get("border"))
            el["border"] = normalized_border  # already "{w}px {style} {color}" or None

        normalized.append(el)

    return normalized


def _validate_template_background(background_color: str, background_image: str) -> tuple:
    """Same allowlists as validate_elements_config, applied to the
    template's own top-level background fields (L-1). background_color must
    be a safe CSS color (falls back to white rather than rejecting — a
    template row must never end up with an invalid/empty color driving the
    page background); background_image must be a same-origin asset path or
    data: URI, else rejected outright (mirrors the per-element image rule)."""
    safe_color = validate_color(background_color) or "#ffffff"
    image = (background_image or "").strip()
    if image and not is_safe_asset_src(image):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "background_image must be an uploaded asset path "
                "(/uploads/... or /certificate-files/...) or a data:image/... URI"
            ),
        )
    return safe_color, image


# ---------------------------------------------------------------------------
# Scoping helpers
# ---------------------------------------------------------------------------


def _visible_query(db: Session, current_user: User):
    """Templates the current user may LIST/READ: own rows, admin sees all,
    everyone (instructor or admin) also sees is_global rows."""
    if current_user.role in ("admin", "superadmin"):
        return db.query(Certificate)
    return db.query(Certificate).filter(
        or_(Certificate.post_author == current_user.id, Certificate.is_global == True)  # noqa: E712
    )


def _get_visible_or_404(db: Session, current_user: User, template_id: int) -> Certificate:
    template = _visible_query(db, current_user).filter(Certificate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


def _assert_editable(current_user: User, template: Certificate) -> None:
    """Global templates are read-only to non-owning instructors — even if an
    instructor authored one that an admin later marked global, editing stays
    restricted to admins + the original author (own-row edits keep working)."""
    if current_user.role in ("admin", "superadmin"):
        return
    if template.post_author != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This is a global template — read-only for instructors"
                if template.is_global
                else "Not authorized to modify this template"
            ),
        )


def _invalidate_rendered_caches_for_template(db: Session, template_id: int) -> int:
    """Clear the cached PDF/PNG/WebP for every IssuedCertificate that
    resolves to this template row (M-2: a template PUT must not leave stale
    renders being served for certificates already using it).

    Bounded by the number of certificates actually issued against this
    template — for a template with heavy issuance volume this is O(n) file
    stats + unlinks done synchronously in the request; acceptable at current
    scale (a certificate template is edited far less often than issued), but
    worth revisiting with a background task if a template ever accumulates
    thousands of issued certificates.
    """
    issued_rows = db.query(IssuedCertificate).filter(
        IssuedCertificate.certificate_id == template_id
    ).all()
    for row in issued_rows:
        try:
            CertificateService.clear_html_pdf_cache(row)
            CertificateService.clear_png_cache(row)
            CertificateService.clear_webp_cache(row)
        except Exception:
            logger.warning(
                "certificate_designer: cache invalidation failed for issued certificate %s",
                getattr(row, "id", "?"), exc_info=True,
            )
    return len(issued_rows)


# ---------------------------------------------------------------------------
# Designer thumbnails (Task 8 fix round, D-8): seed_designer_templates.py's
# best-effort Chrome render writes PNGs to certificates/thumbnails/
# designer-{id}.png. That directory is served by the existing
# `/certificate-files` static mount (app/main.py), so surfacing a thumbnail
# URL here is a pure file-existence check — no new endpoint, no new DB
# column. When the file isn't there (Chrome unavailable at seed time, or a
# template with no render yet), `thumbnail` is None and the frontend
# (TemplateGallery.tsx) falls back to its existing CSS-swatch placeholder.
# ---------------------------------------------------------------------------
_THUMBNAILS_DIR = Path(__file__).resolve().parents[2] / "certificates" / "thumbnails"


def designer_thumbnail_url(template_id: int) -> Optional[str]:
    path = _THUMBNAILS_DIR / f"designer-{template_id}.png"
    if path.is_file():
        return f"/certificate-files/thumbnails/designer-{template_id}.png"
    return None


def _to_out(template: Certificate, current_user: User) -> Dict[str, Any]:
    return {
        "id": template.id,
        "name": template.post_title,
        "description": template.post_content or "",
        "orientation": template.certificate_orientation,
        "certificate_width": template.certificate_width if template.certificate_width is not None else (1080 if template.certificate_orientation == "portrait" else 1400),
        "certificate_height": template.certificate_height if template.certificate_height is not None else (1400 if template.certificate_orientation == "portrait" else 1080),
        "background_color": template.background_color,
        "background_image": template.background_image or "",
        "elements_config": template.elements_config or [],
        "is_global": bool(template.is_global),
        "is_own": template.post_author == current_user.id,
        "post_author": template.post_author,
        "created_at": template.post_date,
        "updated_at": template.post_modified,
        "thumbnail": designer_thumbnail_url(template.id),
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[DesignerTemplateOut])
async def list_designer_templates(
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
):
    """Own templates; admin sees all; every instructor also sees is_global
    templates (read-only to them)."""
    templates = _visible_query(db, current_user).order_by(Certificate.id.desc()).all()
    return [_to_out(t, current_user) for t in templates]


@router.post("/", response_model=DesignerTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_designer_template(
    payload: DesignerTemplateCreate,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
):
    elements = validate_elements_config(payload.elements_config)
    safe_bg_color, safe_bg_image = _validate_template_background(
        payload.background_color, payload.background_image
    )

    new_template = Certificate(
        post_author=current_user.id,
        post_title=payload.name,
        post_content=payload.description or "",
        post_status="publish",
        post_type="tutor_certificates",
        post_name="",  # deliberately blank: elements_config path, not a legacy slug file
        certificate_orientation=payload.orientation,
        certificate_width=payload.certificate_width,
        certificate_height=payload.certificate_height,
        background_color=safe_bg_color,
        background_image=safe_bg_image,
        elements_config=elements,
        is_global=False,
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return _to_out(new_template, current_user)


@router.put("/{template_id}", response_model=DesignerTemplateOut)
async def update_designer_template(
    template_id: int,
    payload: DesignerTemplateUpdate,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
):
    template = _get_visible_or_404(db, current_user, template_id)
    _assert_editable(current_user, template)

    if payload.name is not None:
        template.post_title = payload.name
    if payload.description is not None:
        template.post_content = payload.description
    if payload.orientation is not None:
        template.certificate_orientation = payload.orientation
    if payload.certificate_width is not None:
        template.certificate_width = payload.certificate_width
    if payload.certificate_height is not None:
        template.certificate_height = payload.certificate_height
    if payload.background_color is not None or payload.background_image is not None:
        safe_bg_color, safe_bg_image = _validate_template_background(
            payload.background_color if payload.background_color is not None else template.background_color,
            payload.background_image if payload.background_image is not None else template.background_image,
        )
        template.background_color = safe_bg_color
        template.background_image = safe_bg_image
    if payload.elements_config is not None:
        template.elements_config = validate_elements_config(payload.elements_config)
    if payload.is_global is not None:
        # Only admins may toggle global visibility — an instructor marking
        # their own template global would leak it to every other instructor.
        if current_user.role not in ("admin", "superadmin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can mark a template global",
            )
        template.is_global = payload.is_global

    template.post_modified = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)

    # M-2: an edited design (colors, layout, elements, background) must not
    # keep serving a stale PDF/PNG/WebP for certificates already issued
    # against this template — clear every one of their render caches so the
    # next view/download re-renders from the corrected elements_config.
    _invalidate_rendered_caches_for_template(db, template.id)

    return _to_out(template, current_user)


@router.delete("/{template_id}")
async def delete_designer_template(
    template_id: int,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
):
    template = _get_visible_or_404(db, current_user, template_id)
    _assert_editable(current_user, template)

    # Blocked when referenced — by a course's chosen template, or by any
    # issued certificate (spec Task 6 binding: 409, not a hard delete that
    # would orphan a course setting or an already-issued certificate's row).
    course_ref = db.query(Course.id).filter(
        Course.certificate_template == str(template.id)
    ).first()
    if course_ref:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template is assigned to a course and cannot be deleted",
        )
    issued_ref = db.query(IssuedCertificate.id).filter(
        IssuedCertificate.certificate_id == template.id
    ).first()
    if issued_ref:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template has issued certificates and cannot be deleted",
        )

    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}


@router.post("/{template_id}/duplicate", response_model=DesignerTemplateOut, status_code=status.HTTP_201_CREATED)
async def duplicate_designer_template(
    template_id: int,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
):
    """Copy any VISIBLE template (own or global) into a new OWN row — the
    usual way an instructor starts from a global template without being able
    to edit the shared original."""
    source = _get_visible_or_404(db, current_user, template_id)

    copy = Certificate(
        post_author=current_user.id,
        post_title=f"{source.post_title} (Copy)",
        post_content=source.post_content or "",
        post_status="publish",
        post_type="tutor_certificates",
        post_name="",
        certificate_orientation=source.certificate_orientation,
        certificate_width=source.certificate_width,
        certificate_height=source.certificate_height,
        background_color=source.background_color,
        background_image=source.background_image or "",
        elements_config=source.elements_config or [],
        is_global=False,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return _to_out(copy, current_user)


@router.post("/{template_id}/preview")
async def preview_designer_template(
    template_id: int,
    payload: DesignerPreviewRequest = None,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
):
    """Render a preview of a designer template with sample data.

    Tries the real Chrome-rendered HTML->PDF path first (matches exactly
    what a student would receive); falls back to the ReportLab renderer when
    Chrome is unavailable, so this endpoint never 500s in an environment
    without headless Chrome (plan-noted: likely the case in this test box).
    Always returns a data: URI, mirroring the admin preview endpoint's shape.
    """
    import base64
    import os
    import tempfile

    from app.services.certificate_html_renderer import build_certificate_html

    template = _get_visible_or_404(db, current_user, template_id)

    values = sample_values(f"PREVIEW-{template.id}")
    if payload and payload.values:
        # Only known keys — an arbitrary payload must not inject unrelated
        # tokens into the render.
        for key in ("student_name", "course_name", "completion_date",
                    "certificate_id", "instructor_name", "verify_url"):
            if key in payload.values and payload.values[key]:
                values[key] = str(payload.values[key])[:300]

    # 1) Try the real Chrome HTML render (same path production issuance uses).
    try:
        html_content = build_certificate_html(template, values)
        pdf_bytes = CertificateService._render_local_html_pdf_via_chrome(
            html_content, template.certificate_width, template.certificate_height
        )
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        return {
            "preview_url": f"data:application/pdf;base64,{pdf_b64}",
            "preview_type": "pdf",
            "renderer": "chrome",
            "template_id": template_id,
            "sample_data": values,
        }
    except Exception:
        logger.info(
            "certificate_designer preview: Chrome render unavailable for template %s, "
            "falling back to ReportLab", template_id, exc_info=True
        )

    # 2) ReportLab fallback — deterministic, no external browser dependency.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        template_design = {
            "dimensions": {
                "width": template.certificate_width,
                "height": template.certificate_height,
            },
            "background": {
                "type": "image" if template.background_image else "color",
                "value": template.background_color,
                "image_url": template.background_image,
            },
            "elements": template.elements_config or [],
        }
        sample_data = {
            "student_name": values["student_name"],
            "course_title": values["course_name"],
            "course_name": values["course_name"],
            "completion_date": values["completion_date"],
            "certificate_id": values["certificate_id"],
            "instructor_name": values["instructor_name"],
            "verify_url": values["verify_url"],
        }
        CertificateService.render_template_preview(template_design, sample_data, temp_path)
        with open(temp_path, "rb") as fh:
            pdf_bytes = fh.read()
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        return {
            "preview_url": f"data:application/pdf;base64,{pdf_b64}",
            "preview_type": "pdf",
            "renderer": "reportlab",
            "template_id": template_id,
            "sample_data": values,
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
