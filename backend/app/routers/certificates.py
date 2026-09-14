"""
Certificate Router - SashaInfinity LMS API
Handles certificate generation and management
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Response, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import html
import io
import base64

from app.core.database import get_db
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.certificate import Certificate, IssuedCertificate, CertificateElementTemplate
from app.services.auth_service import AuthService
from app.services.certificate_service import CertificateService
from app.schemas.certificate import (
    CertificateResponse,
    CertificateTemplateCreate,
    CertificateTemplateResponse
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Certificate template selection
# ---------------------------------------------------------------------------
# The original design lives in `certificates/template.html` (a self-unpacking
# bundle) and is the DEFAULT. Additional hand-authored designs live in
# `certificates/templates/<slug>.html` and are chosen per-course by the
# instructor. The link is: IssuedCertificate.certificate_id -> Certificate row,
# whose `post_name` slug names the template file. Every template shares the same
# placeholder sentinels ("Logadheenan V M", "Full-Stack Web Development",
# "Gayathri Devi", "June 02, 2026", "CERT-2026-000142") and the same
# `generateQR();` hook, so the string-replacement below works for all of them.
import pathlib as _pathlib

_CERT_ROOT = _pathlib.Path("/app/certificates")
_DEFAULT_TEMPLATE_PATH = _CERT_ROOT / "template.html"
_TEMPLATES_DIR = _CERT_ROOT / "templates"


def resolve_template_path(db: Session, issued_cert) -> _pathlib.Path:
    """Return the HTML template file for an issued certificate.

    Falls back to the default `template.html` when the certificate's template
    row has no slug, the slug names no file on disk, or anything goes wrong —
    so a misconfigured template can never break rendering.
    """
    try:
        template_id = getattr(issued_cert, "certificate_id", None)
        if template_id:
            tpl = db.query(Certificate).filter(Certificate.id == template_id).first()
            slug = (getattr(tpl, "post_name", "") or "").strip() if tpl else ""
            if slug:
                candidate = _TEMPLATES_DIR / f"{slug}.html"
                if candidate.is_file():
                    return candidate
    except Exception:
        pass
    return _DEFAULT_TEMPLATE_PATH


def _esc(value: Optional[str]) -> str:
    """HTML-escape a value before substituting it into a certificate template.

    Student display names, course titles and instructor names are user
    input rendered into a PUBLIC HTML page (the verify portal is reachable
    without auth via the QR code). Without escaping, a display_name like
    ``<img src=x onerror=...>`` executes in every viewer's browser
    (stored XSS). Values land in both text and attribute contexts, so
    quotes are escaped too.
    """
    return html.escape(value if value is not None else "", quote=True)


def _apply_template_placeholders(
    html_template: str,
    *,
    student_name: Optional[str],
    course_title: Optional[str],
    instructor_name: Optional[str],
    completion_date: str,
    cert_id_display: str,
    verification_url: str,
) -> str:
    """Substitute the shared template sentinels with ESCAPED values.

    Every value that originates outside this module (names, titles, dates)
    is html-escaped exactly once, here — the single choke point both the
    /view and /verify-certificate render paths go through.
    """
    esc_student = _esc(student_name if student_name else "Student Name")
    esc_course = _esc(course_title if course_title else "Course Title")
    esc_instructor = _esc(instructor_name if instructor_name else "SashaInfinity")
    esc_date = _esc(completion_date)
    esc_cert_id = _esc(cert_id_display)
    esc_url = _esc(verification_url)

    html_template = html_template.replace("Student Name", esc_student)
    html_template = html_template.replace("Logadheenan V M", esc_student)
    html_template = html_template.replace("Course Title", esc_course)
    html_template = html_template.replace("Full-Stack Web Development", esc_course)
    html_template = html_template.replace("Instructor Name", esc_instructor)
    html_template = html_template.replace("Gayathri Devi", esc_instructor)
    html_template = html_template.replace("June 02, 2026", esc_date)
    html_template = html_template.replace("June 2, 2026", esc_date)
    # Plain cert-ID sentinel used by the new hand-authored templates (their
    # certId + "ID: CERT-2026-000142" caption). Harmless on the default bundle.
    html_template = html_template.replace("CERT-2026-000142", esc_cert_id)
    html_template = html_template.replace(
        'id="certId">CERT-2026-000142</div>', f'id="certId">{esc_cert_id}</div>'
    )
    html_template = html_template.replace(
        'id="verifyUrl">sashainfinity.com/verify</div>', f'id="verifyUrl">{esc_url}</div>'
    )
    return html_template


# ---------------------------------------------------------------------------
# Asset URLs carry a file extension.
#
# Cloudflare's default cache is keyed on the URL's file extension, so the
# extensionless `/api/v1/certificates/image/<id>/<hash>` came back
# `cf-cache-status: DYNAMIC` on every request — the origin's `Cache-Control:
# public, max-age=86400` never took effect at the edge, and each view pulled
# the full 1.36MB from origin. The bytes are identical to
# `/certificate-files/*.png`, which the edge caches happily; the only
# difference was the extension.
#
# Ending the path in `.webp` / `.png` / `.pdf` puts these responses back in
# the edge's cacheable set. The extension is optional so every link already in
# the wild — including issued certificates' stored URLs — keeps resolving.
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = (".webp", ".png")
_PDF_EXTENSIONS = (".pdf",)


def split_asset_ext(value: str, allowed: tuple) -> tuple:
    """Split a trailing asset extension off a path segment.

    Returns `(bare_value, extension)`, with the extension lower-cased, or
    `(value, None)` when it carries none we serve. The bare value is what the
    certificate lookup must use — matching on the suffixed string 404s.
    """
    lowered = (value or "").lower()
    for ext in allowed:
        if lowered.endswith(ext) and len(lowered) > len(ext):
            return value[: -len(ext)], ext
    return value, None


def negotiate_image_format(extension, accept_header) -> str:
    """Pick the image encoding for a certificate request.

    An explicit extension always wins — that URL names a specific file. With
    none, fall back to the Accept header: browsers advertise `image/webp` and
    get the ~100KB WebP, while anything that doesn't ask for it keeps the PNG.
    That last part matters for LinkedIn, which fetches og:image server-side,
    never advertises WebP, and would otherwise lose every share preview.
    """
    if extension == ".webp":
        return "webp"
    if extension == ".png":
        return "png"
    if accept_header and "image/webp" in accept_header.lower():
        return "webp"
    return "png"


def certificate_download_url(certificate) -> str:
    """Public download URL that renders the certificate's ACTUAL design.

    `IssuedCertificate.certificate_download_url` stores the path of a one-off
    ReportLab PDF written when the certificate was first issued. That file is
    frozen: it keeps serving the old ReportLab layout even after the course's
    template changes, so a student downloading from the verification page got a
    different design from the one shown on screen. Deriving the URL from the
    certificate's own identity instead sends every download through the same
    HTML renderer the preview uses, so the two can never drift apart.

    Falls back to the stored column only when the certificate predates secure
    IDs and there is nothing to derive a URL from.
    """
    secure_id = getattr(certificate, "secure_certificate_id", "") or ""
    cert_hash = getattr(certificate, "certificate_hash", "") or ""
    if secure_id and cert_hash:
        # `.pdf` so Cloudflare will edge-cache the response — see the note above
        # split_asset_ext().
        return f"/api/v1/certificates/download-pdf/{secure_id}/{cert_hash}.pdf"
    return getattr(certificate, "certificate_download_url", "") or ""


@router.get("/", response_model=List[CertificateResponse])
async def get_user_certificates(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all certificates earned by the user
    """
    certificates = db.query(IssuedCertificate).filter(
        IssuedCertificate.user_id == current_user.id
    ).all()

    return [
        {
            "id": cert.id,
            "course_id": cert.course_id,
            "course_title": cert.course.post_title,
            "student_name": current_user.display_name,
            "instructor_name": cert.course.instructor.display_name,
            "completion_date": cert.completion_date,
            "certificate_url": certificate_download_url(cert),
            "verification_code": cert.certificate_hash,
            "issued_at": cert.created_at,
            # Paused certificates (course completion regressed) stay listed so
            # the student sees WHY the file no longer loads instead of a
            # silent dead link; they revive automatically on re-completion.
            "is_valid": bool(cert.is_valid),
            # Issue 4: public verification URL keyed by the certificate's
            # secure ID + hash, so the credential is shareable by its own
            # identity rather than only by raw hash.
            "secure_certificate_id": cert.secure_certificate_id or "",
            "public_url": (
                f"/verify-certificate/{cert.certificate_hash}"
                if cert.certificate_hash else ""
            ),
        }
        for cert in certificates
    ]

@router.get("/course/{course_id}")
async def get_certificate_by_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """Get certificate for a specific course"""
    cert = db.query(IssuedCertificate).filter(
        IssuedCertificate.course_id == course_id,
        IssuedCertificate.user_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    course = db.query(Course).filter(Course.id == course_id).first()
    student = db.query(User).filter(User.id == current_user.id).first()
    return {
        "id": cert.id,
        "course_id": cert.course_id,
        "course_title": course.post_title if course else cert.certificate_title,
        "student_name": student.display_name or student.user_login if student else "Student",
        "instructor_name": "Sashainfinity",
        "issue_date": cert.created_at,  # IssuedCertificate has no issue_date column; created_at is the issuance timestamp
        "verification_code": cert.certificate_hash,
        "secure_certificate_id": cert.secure_certificate_id,
        "certificate_hash": cert.certificate_hash
    }

@router.post("/generate/{course_id}")
async def generate_certificate(
    course_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate (or return the existing) certificate for a completed course.
    Thin wrapper over the central `issue_certificate_for_enrollment` helper
    so manual, auto (on progress=100%), and assignment/quiz-gated paths
    all share the same logic + SS2 eligibility hook.
    """
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id,
        Enrollment.completion_date.isnot(None),
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course not completed or not enrolled",
        )

    cert, newly_issued = CertificateService.issue_certificate_for_enrollment(db, enrollment)
    if not cert:
        # The tracker columns were just recomputed by the eligibility check,
        # so the message can say exactly what's missing instead of a bare
        # "failed" that looks like a bug.
        pct = enrollment.course_progress_percentage or 0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Certificate not available yet — course is {pct}% complete. "
                "Finish every lesson, quiz and assignment to unlock it "
                f"({enrollment.completed_lessons or 0}/{enrollment.total_lessons or 0} lessons, "
                f"{enrollment.completed_quizzes or 0}/{enrollment.total_quizzes or 0} quizzes)."
            ),
        )

    return {
        "certificate_id": cert.id,
        "message": "Certificate generated successfully" if newly_issued else "Certificate already generated",
        "certificate_url": certificate_download_url(cert),
    }


@router.post("/regenerate/{course_id}")
async def regenerate_certificate(
    course_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate the certificate: delete the existing row + file, then run
    the central issuance helper. Useful when the initial PDF generation
    failed (the row was left with an empty URL).
    """
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id,
        Enrollment.completion_date.isnot(None),
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course not completed or not enrolled",
        )

    try:
        existing_certificate = db.query(IssuedCertificate).filter(
            IssuedCertificate.course_id == course_id,
            IssuedCertificate.user_id == current_user.id,
        ).first()

        if existing_certificate:
            # Best-effort file cleanup, then drop the row.
            import os
            if existing_certificate.certificate_download_url:
                file_path = existing_certificate.certificate_download_url.replace(
                    "/certificate-files/", "certificates/"
                )
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass  # Stale file is harmless; log-only behaviour acceptable.
            # Drop the cached HTML-rendered PDF + image too.
            CertificateService.clear_html_pdf_cache(existing_certificate)
            CertificateService.clear_png_cache(existing_certificate)
            CertificateService.clear_webp_cache(existing_certificate)
            db.delete(existing_certificate)
            enrollment.certificate_id = None
            enrollment.certificate_url = None
            db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear existing certificate: {e}",
        )

    cert, newly_issued = CertificateService.issue_certificate_for_enrollment(db, enrollment)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate certificate",
        )

    return {
        "certificate_id": cert.id,
        "message": "Certificate regenerated successfully",
        "certificate_url": certificate_download_url(cert),
    }

@router.get("/view/{certificate_id}")
async def view_certificate_html(
    certificate_id: int,
    db: Session = Depends(get_db)
):
    """
    View certificate as beautiful HTML page.

    Public (no auth): opened in a new tab via `window.open()`, which cannot
    attach the JWT, so requiring auth would always 401. Consistent with the
    public verify-certificate page.
    """
    from fastapi.responses import HTMLResponse
    import pathlib

    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.id == certificate_id
    ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    # Get related data
    student = db.query(User).filter(User.id == certificate.user_id).first()
    course = db.query(Course).filter(Course.id == certificate.course_id).first()

    # Format dates
    if certificate.completion_date:
        completion_date = certificate.completion_date.strftime("%B %d, %Y")
    else:
        completion_date = datetime.now().strftime("%B %d, %Y")

    # Generate verification URL.
    # `base_url` is the app origin (nginx proxies both the SPA and /api/v1 on
    # it), used below for the backend download-html-pdf link. The public,
    # scannable verification link points at the frontend portal route
    # /verify-certificate/:certificateId, which looks the cert up by hash.
    from app.core.config import get_settings
    base_url = getattr(get_settings(), "FRONTEND_URL", "https://lms.sashainfinity.com").rstrip("/")
    verification_url = f"{base_url}/verify-certificate/{certificate.certificate_hash}"
    cert_id_display = f"CERT-{datetime.now().year}-{str(certificate.id).zfill(6)}"

    # Unified render path (Task 6): a template with elements_config (and no
    # legacy post_name slug) renders directly from the builder design —
    # bypass the sentinel-substitution file path entirely.
    dynamic_html = CertificateService.build_certificate_html_for_issued(db, certificate)
    if dynamic_html is not None:
        return HTMLResponse(content=dynamic_html, headers={"Cache-Control": "public, max-age=3600"})

    # Read HTML template (per-course selection, default fallback)
    import os
    template_path = resolve_template_path(db, certificate)
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_template = f.read()
    except FileNotFoundError:
        # Fallback if template doesn't exist
        return {"error": "Certificate template not found"}

    # Replace placeholders with actual data (values HTML-escaped — see
    # _apply_template_placeholders; the page is public, so names/titles
    # are stored-XSS vectors).
    html_template = _apply_template_placeholders(
        html_template,
        student_name=student.display_name if student else None,
        course_title=course.post_title if course else None,
        instructor_name=(
            course.instructor.display_name
            if course and getattr(course, "instructor", None)
            else None
        ),
        completion_date=completion_date,
        cert_id_display=cert_id_display,
        verification_url=verification_url,
    )

    # Remove localStorage and edit scripts for viewed certificate (make it static)
    html_template = html_template.replace("contenteditable=\"true\"", "")
    html_template = html_template.replace('class="editable"', "")

    # Truncate cert ID for overlay display (max 10 chars)
    cert_id_short = cert_id_display[-10:] if len(cert_id_display) > 10 else cert_id_display

    # Update QR code generation script with actual verification URL
    qr_script = f"""
    (function() {{
        const certIdValue = "{cert_id_display}";
        const certIdShort = "{cert_id_short}";
        const verificationUrl = "{verification_url}";

        // Add CSS for verification overlay text overflow and print layout
        const style = document.createElement('style');
        style.textContent = `
            #vId, #vLink, #vName, #vCourse, #vDate {{
                max-width: 180px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                display: inline-block;
            }}
            .vt-url {{ display: none !important; }}
            @media print {{
                @page {{
                    margin: 0 !important;
                    size: landscape;
                }}
                * {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    color-adjust: exact !important;
                }}
                html, body {{
                    margin: 0 !important;
                    padding: 0 !important;
                    width: 100% !important;
                    height: 100% !important;
                    overflow: visible !important;
                }}
                body > *:not(.no-print) {{
                    display: none !important;
                }}
                .certificate-container, .no-print {{
                    margin: 0 !important;
                    padding: 0 !important;
                    width: 100vw !important;
                    height: 100vh !important;
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                }}
                button, .no-print, button *, .no-print * {{
                    display: none !important;
                }}
            }}
        `;
        document.head.appendChild(style);

        function updateCertificate() {{
            const certIdElem = document.getElementById('vtCode');
            if (certIdElem) certIdElem.textContent = 'ID: ' + certIdShort;

            // Hide URL element
            const verifyUrlElem = document.querySelector('.vt-url');
            if (verifyUrlElem) verifyUrlElem.style.display = 'none';

            // Update verification overlay with truncated values
            const vIdElem = document.getElementById('vId');
            if (vIdElem) vIdElem.textContent = certIdShort;
            const vLinkElem = document.getElementById('vLink');
            if (vLinkElem) {{
                vLinkElem.textContent = certIdShort;
                vLinkElem.href = verificationUrl;
            }}

            const qrContainer = document.getElementById('qrcode');
            if (qrContainer && window.QRCode) {{
                qrContainer.innerHTML = '';
                new window.QRCode(qrContainer, {{ text: verificationUrl, width: 96, height: 96, colorDark: '#0b2444', colorLight: '#ffffff', correctLevel: window.QRCode.CorrectLevel.M }});
            }} else {{
                console.warn('QR code container or QRCode library not found');
            }}
        }}

        // Add download button for HTML-to-PDF
        function addDownloadButton() {{
            const printBtn = document.getElementById('printBtn');
            if (printBtn && !document.getElementById('downloadPdfBtn')) {{
                const downloadUrl = "{base_url}/api/v1/certificates/download-html-pdf/{certificate.secure_certificate_id}/{certificate.certificate_hash}";
                const downloadBtn = printBtn.cloneNode(true);
                downloadBtn.id = 'downloadPdfBtn';
                downloadBtn.textContent = 'Download PDF';
                downloadBtn.classList.add('no-print');
                downloadBtn.onclick = function() {{ window.location.href = downloadUrl; }};
                printBtn.parentNode.insertBefore(downloadBtn, printBtn);
            }}
        }}

        // Wait for bundle to finish unpacking before updating
        if (document.getElementById('__bundler_loading')) {{
            // Bundle still loading, wait for it
            const observer = new MutationObserver(function(mutations) {{
                mutations.forEach(function(mutation) {{
                    if (mutation.type === 'childList' && !document.getElementById('__bundler_loading')) {{
                        updateCertificate();
                        addDownloadButton();
                        observer.disconnect();
                    }}
                }});
            }});
            observer.observe(document.body, {{ childList: true, subtree: true }});
            // Fallback: try after a delay
            setTimeout(function() {{ updateCertificate(); addDownloadButton(); }}, 2000);
        }} else {{
            updateCertificate();
            addDownloadButton();
        }}
    }})();
    """
    # Replace the generateQR function call at the end
    html_template = html_template.replace("generateQR();", qr_script)

    return HTMLResponse(
        content=html_template,
        headers={
            "Cache-Control": "public, max-age=3600",
        }
    )


@router.get("/download/{certificate_id}")
async def download_certificate(
    certificate_id: int,
    db: Session = Depends(get_db)
):
    """
    Download certificate as PDF rendered from the HTML template (matches the
    on-screen preview). Serves the PDF directly — no cross-origin redirect.

    Public (no auth): this is opened via `window.open()` in a new browser tab,
    which cannot attach the JWT Authorization header, so requiring auth would
    always 401. Consistent with the other public download/verify endpoints
    (download-html-pdf, download-pdf, verify-certificate) — certificates are
    shareable, verifiable credentials.
    """
    import asyncio

    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.id == certificate_id
    ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    pdf_content = await asyncio.to_thread(
        CertificateService.get_or_render_html_pdf, certificate
    )
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{certificate_id}.pdf",
            "Cache-Control": "public, max-age=3600",
        },
    )

@router.get("/admin/download/{enrollment_id}")
async def admin_download_certificate(
    enrollment_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to download certificate for any enrollment
    """
    # Find the issued certificate for this enrollment
    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.enrollment_id == enrollment_id
    ).first()

    if not certificate:
        # Try to find by user_id and course_id
        enrollment = db.query(Enrollment).filter(
            Enrollment.id == enrollment_id
        ).first()

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found"
            )

        certificate = db.query(IssuedCertificate).filter(
            IssuedCertificate.user_id == enrollment.user_id,
            IssuedCertificate.course_id == enrollment.course_id
        ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found for this enrollment"
        )

    # Render the HTML template design (matches the on-screen preview).
    import asyncio
    pdf_content = await asyncio.to_thread(
        CertificateService.get_or_render_html_pdf, certificate
    )

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{enrollment_id}.pdf"
        }
    )

@router.get("/verify-certificate")
async def verify_certificate_page(
    cert_id: str = Query(..., alias="id", description="Certificate secure ID"),
    cert_hash: str = Query(..., alias="hash", description="Certificate verification hash"),
    full: int = Query(0, description="1 = serve the full interactive bundle (used by the PDF/PNG renderer); default = fast image view"),
    db: Session = Depends(get_db)
):
    """
    Public certificate verification page.

    By default serves a FAST, lightweight page: a single pre-rendered
    certificate image (no 1.1MB self-unpacking JS bundle) so the on-screen
    view / preview iframe loads near-instantly. The Chrome PDF/PNG renderer
    requests `?full=1` to get the heavy interactive bundle it rasterizes from.
    Accessible via QR code scan via /api/v1/certificates/verify-certificate?id=X&hash=Y
    """
    from fastapi.responses import HTMLResponse
    import pathlib

    # Find certificate by secure ID and hash
    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.secure_certificate_id == cert_id,
        IssuedCertificate.certificate_hash == cert_hash
    ).first()

    # Fast path: serve the lightweight image-based view (default).
    if not full and certificate:
        # `.webp` explicitly: this page is what a person looks at, and the WebP
        # is ~100KB against the PNG's 1.36MB. The extension also gets the file
        # into Cloudflare's cache, so the second viewer pays nothing.
        image_url = f"/api/v1/certificates/image/{cert_id}/{cert_hash}.webp"
        fast_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Certificate of Excellence - SashaInfinity</title>
<style>
  html, body {{ margin:0; padding:0; background:#ffffff; height:100%; }}
  .wrap {{ display:flex; align-items:center; justify-content:center; min-height:100vh; }}
  img {{ max-width:100%; max-height:100vh; width:auto; height:auto; display:block; }}
  @media print {{
    @page {{ size:A4 landscape; margin:0; }}
    html, body {{ background:#ffffff; }}
    .wrap {{ min-height:auto; }}
    img {{ width:100%; height:auto; max-height:none; }}
  }}
</style>
</head>
<body>
  <div class="wrap"><img src="{image_url}" alt="Certificate of Completion"></div>
</body>
</html>"""
        return HTMLResponse(content=fast_html, headers={"Cache-Control": "public, max-age=3600"})

    if not certificate:
        error_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certificate Not Found - SashaInfinity</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h1 { color: #E8701A; }
        .icon { font-size: 60px; margin-bottom: 20px; }
        a { color: #E8701A; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">❌</div>
        <h1>Certificate Not Found</h1>
        <p>The certificate you are trying to verify is invalid or does not exist.</p>
        <p>Please check the QR code or verification link and try again.</p>
        <br>
        <a href="https://sashainfinity.com">Return to SashaInfinity</a>
    </div>
</body>
</html>"""
        return HTMLResponse(content=error_html, status_code=404)

    student = db.query(User).filter(User.id == certificate.user_id).first()
    course = db.query(Course).filter(Course.id == certificate.course_id).first()

    if certificate.completion_date:
        completion_date = certificate.completion_date.strftime("%B %d, %Y")
    else:
        completion_date = datetime.now().strftime("%B %d, %Y")

    # `base_url` is the app origin (nginx serves the SPA and proxies /api/v1
    # here), used for the backend download-html-pdf link below. The QR /
    # displayed link is the public frontend verification portal, keyed by hash.
    from app.core.config import get_settings
    base_url = getattr(get_settings(), "FRONTEND_URL", "https://lms.sashainfinity.com").rstrip("/")
    verification_url = f"{base_url}/verify-certificate/{certificate.certificate_hash}"
    year = completion_date.split()[-1] if completion_date else "2026"
    cert_id_display = f"CERT-{year}-{str(certificate.id).zfill(6)}"

    # Unified render path (Task 6): elements_config templates render
    # directly — this is also the URL the local-file Chrome PDF/PNG renderer
    # used to navigate to for the legacy design; the elements_config path
    # instead renders straight to a local file (see certificate_service
    # ._render_local_html_pdf_via_chrome), so this branch only serves a
    # human opening the link directly.
    dynamic_html = CertificateService.build_certificate_html_for_issued(db, certificate)
    if dynamic_html is not None:
        return HTMLResponse(content=dynamic_html, headers={"Cache-Control": "public, max-age=3600"})

    template_path = resolve_template_path(db, certificate)
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_template = f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<p>Certificate template not found</p>")

    html_template = _apply_template_placeholders(
        html_template,
        student_name=student.display_name if student else None,
        course_title=course.post_title if course else None,
        instructor_name=(
            course.instructor.display_name
            if course and getattr(course, "instructor", None)
            else None
        ),
        completion_date=completion_date,
        cert_id_display=cert_id_display,
        verification_url=verification_url,
    )

    html_template = html_template.replace("contenteditable=\"true\"", "")
    html_template = html_template.replace('class="editable"', "")
    html_template = html_template.replace("contenteditable=true", "")

    # Truncate cert ID for overlay display (max 10 chars)
    cert_id_short = cert_id_display[-10:] if len(cert_id_display) > 10 else cert_id_display

    qr_script = f"""
    (function() {{
        const certIdValue = "{cert_id_display}";
        const certIdShort = "{cert_id_short}";
        const verificationUrl = "{verification_url}";

        // Add CSS for verification overlay text overflow and print layout
        const style = document.createElement('style');
        style.textContent = `
            #vId, #vLink, #vName, #vCourse, #vDate {{
                max-width: 180px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                display: inline-block;
            }}
            .vt-url {{ display: none !important; }}
            @media print {{
                @page {{
                    size: A4 landscape;
                    margin: 0;
                }}
                * {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    color-adjust: exact !important;
                }}
                html, body {{
                    margin: 0 !important;
                    padding: 0 !important;
                    width: 100% !important;
                    height: 100% !important;
                    background: #ffffff !important;
                    overflow: visible !important;
                }}
                /* Hide on-screen chrome so the PDF is ONLY the certificate. */
                .toolbar, .no-print, button, button *, #overlay {{
                    display: none !important;
                }}
                /* The certificate lives in .stage > #cert (native 1200x850,
                   ratio ~1.412 ≈ A4 landscape). Flatten the dark presentation
                   background and center the card so it fills the page. */
                .stage {{
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                    box-shadow: none !important;
                    width: 100% !important;
                    min-height: 100vh !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }}
                #cert, .cert {{
                    margin: 0 auto !important;
                    box-shadow: none !important;
                }}
            }}
        `;
        document.head.appendChild(style);

        function updateCertificate() {{
            const certIdElem = document.getElementById('vtCode');
            if (certIdElem) certIdElem.textContent = 'ID: ' + certIdShort;

            // Hide URL element
            const verifyUrlElem = document.querySelector('.vt-url');
            if (verifyUrlElem) verifyUrlElem.style.display = 'none';

            // Update verification overlay with truncated values
            const vIdElem = document.getElementById('vId');
            if (vIdElem) vIdElem.textContent = certIdShort;
            const vLinkElem = document.getElementById('vLink');
            if (vLinkElem) {{
                vLinkElem.textContent = certIdShort;
                vLinkElem.href = verificationUrl;
            }}

            const qrContainer = document.getElementById('qrcode');
            if (qrContainer && window.QRCode) {{
                qrContainer.innerHTML = '';
                new window.QRCode(qrContainer, {{ text: verificationUrl, width: 96, height: 96, colorDark: '#0b2444', colorLight: '#ffffff', correctLevel: window.QRCode.CorrectLevel.M }});
            }} else {{
                console.warn('QR code container or QRCode library not found');
            }}
        }}

        // Add download button for HTML-to-PDF
        function addDownloadButton() {{
            const printBtn = document.getElementById('printBtn');
            if (printBtn && !document.getElementById('downloadPdfBtn')) {{
                const downloadUrl = "{base_url}/api/v1/certificates/download-html-pdf/{cert_id}/{cert_hash}";
                const downloadBtn = printBtn.cloneNode(true);
                downloadBtn.id = 'downloadPdfBtn';
                downloadBtn.textContent = 'Download PDF';
                downloadBtn.classList.add('no-print');
                downloadBtn.onclick = function() {{ window.location.href = downloadUrl; }};
                printBtn.parentNode.insertBefore(downloadBtn, printBtn);
            }}
        }}

        // Wait for bundle to finish unpacking before updating
        if (document.getElementById('__bundler_loading')) {{
            const observer = new MutationObserver(function(mutations) {{
                mutations.forEach(function(mutation) {{
                    if (mutation.type === 'childList' && !document.getElementById('__bundler_loading')) {{
                        updateCertificate();
                        addDownloadButton();
                        observer.disconnect();
                    }}
                }});
            }});
            observer.observe(document.body, {{ childList: true, subtree: true }});
            setTimeout(function() {{ updateCertificate(); addDownloadButton(); }}, 2000);
        }} else {{
            updateCertificate();
            addDownloadButton();
        }}
    }})();
    """
    html_template = html_template.replace("generateQR();", qr_script)

    return HTMLResponse(
        content=html_template,
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/image/{cert_id}/{cert_hash}")
async def certificate_image(
    cert_id: str,
    cert_hash: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public image of the certificate (cached). Used by the fast on-screen view
    so the preview loads instantly instead of downloading + JS-unpacking the
    1.1MB interactive bundle.

    Serves WebP (~100KB) to anything that advertises it and the PNG (~1.36MB)
    to everything else. The URL may end in `.webp` or `.png` to name a format
    outright — and to give Cloudflare an extension it will edge-cache.
    """
    import asyncio

    cert_hash, extension = split_asset_ext(cert_hash, _IMAGE_EXTENSIONS)

    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.secure_certificate_id == cert_id,
        IssuedCertificate.certificate_hash == cert_hash
    ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    image = None
    media_type = "image/png"
    if negotiate_image_format(extension, request.headers.get("accept")) == "webp":
        image = await asyncio.to_thread(
            CertificateService.get_or_render_html_webp, certificate
        )
        media_type = "image/webp"

    if not image:
        # No WebP wanted, or the conversion failed — the PNG is the source of
        # truth and always renders.
        image = await asyncio.to_thread(
            CertificateService.get_or_render_html_png, certificate
        )
        media_type = "image/png"

    if not image:
        # Rendering failed — bounce to the full interactive page so the user
        # still sees the certificate.
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"/api/v1/certificates/verify-certificate?id={cert_id}&hash={cert_hash}&full=1",
            status_code=302,
        )

    headers = {"Cache-Control": "public, max-age=86400"}
    if not extension:
        # Without an extension this URL answers either format depending on the
        # request, so it must not be cached as if it were one of them. Say so —
        # and note that Cloudflare ignores Vary on anything but Accept-Encoding,
        # which is precisely why the cacheable links carry a real extension
        # instead of relying on negotiation.
        headers["Vary"] = "Accept"

    return Response(content=image, media_type=media_type, headers=headers)


# ---------------------------------------------------------------------------
# Social sharing (LinkedIn)
#
# LinkedIn's `share-offsite` endpoint only ever shares a URL — it renders the
# preview card from the Open Graph tags of that URL, and it cannot carry post
# text. So sharing a certificate needs two pieces:
#
#   1. A crawlable landing page (`/share/{id}/{hash}`) whose og:image IS the
#      rendered certificate, so the post preview shows the certificate itself
#      instead of the generic site logo.
#   2. A caption the frontend pre-fills into the LinkedIn composer.
#
# Both derive from the same builder below so the preview and the caption never
# drift apart.
# ---------------------------------------------------------------------------

SASHA_LINKEDIN_PAGE = "https://www.linkedin.com/company/sashainfinity/"
SASHA_LINKEDIN_HANDLE = "@SashaInfinity"

CERTIFICATE_HASHTAGS = [
    "SashaInfinity",
    "Certification",
    "ContinuousLearning",
    "ProfessionalDevelopment",
    "Upskilling",
    "CareerGrowth",
    "LifelongLearning",
]


def _public_base_url(request: Request) -> str:
    """Absolute, publicly reachable origin for this request.

    Prefers the proxy-forwarded host (nginx) so the URL we hand to LinkedIn is
    the exact host the student is browsing; falls back to the configured
    frontend URL when the request carries no usable host header.
    """
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")

    if forwarded_host and "localhost" not in forwarded_host and "127.0.0.1" not in forwarded_host:
        scheme = forwarded_proto or request.url.scheme or "https"
        return f"{scheme}://{forwarded_host}".rstrip("/")

    try:
        from app.core.config import get_settings
        configured = (get_settings().FRONTEND_URL or "").rstrip("/")
        if configured:
            return configured
    except Exception:
        pass

    return f"{request.url.scheme}://{request.url.netloc}".rstrip("/")


def _course_hashtag(course_title: str) -> Optional[str]:
    """Turn a course title into a CamelCase hashtag ("AI For Everyone" ->
    #AIForEveryone). Returns None when nothing usable survives."""
    words = [w for w in "".join(ch if ch.isalnum() else " " for ch in course_title).split() if w]
    tag = "".join(w[:1].upper() + w[1:] for w in words)
    if not tag or not tag[0].isalpha() or len(tag) > 40:
        return None
    return tag


def _build_share_payload(certificate, student, course, request: Request) -> dict:
    """Everything both the OG landing page and the share dialog need."""
    base_url = _public_base_url(request)
    cert_id = certificate.secure_certificate_id
    cert_hash = certificate.certificate_hash

    student_name = (student.display_name or student.user_login) if student else "Student"
    course_title = (course.post_title if course else None) or certificate.certificate_title or "my course"

    completion = certificate.completion_date or certificate.created_at
    completion_label = completion.strftime("%B %Y") if completion else ""

    share_url = f"{base_url}/api/v1/certificates/share/{cert_id}/{cert_hash}"
    # `.png`, not `.webp`: this is og:image. LinkedIn fetches it server-side and
    # its preview rendering is unreliable on WebP, so the share card keeps the
    # PNG — declared as image/png below. The extension still makes it cacheable.
    image_url = f"{base_url}/api/v1/certificates/image/{cert_id}/{cert_hash}.png"
    verify_url = f"{base_url}/api/v1/certificates/verify-certificate?id={cert_id}&hash={cert_hash}"

    hashtags = list(CERTIFICATE_HASHTAGS)
    course_tag = _course_hashtag(course_title)
    if course_tag and course_tag not in hashtags:
        hashtags.insert(1, course_tag)
    hashtag_line = " ".join(f"#{tag}" for tag in hashtags)

    caption = (
        f"🎉 Proud to have successfully completed \"{course_title}\" at SashaInfinity!\n\n"
        "Grateful for the opportunity to learn, grow, and enhance my skills. "
        "Looking forward to applying this knowledge in real-world projects.\n\n"
        f"Thank you, SashaInfinity ({SASHA_LINKEDIN_HANDLE}), for this learning experience!\n\n"
        f"🔗 Verify my certificate: {share_url}\n\n"
        f"{hashtag_line}"
    )

    og_title = f"{student_name} completed {course_title} — SashaInfinity"
    og_description = (
        f"{student_name} successfully completed \"{course_title}\" at SashaInfinity"
        + (f" in {completion_label}" if completion_label else "")
        + ". Verified certificate of completion."
    )

    return {
        "student_name": student_name,
        "course_title": course_title,
        "completion_label": completion_label,
        "certificate_id": cert_id,
        "share_url": share_url,
        "image_url": image_url,
        "verify_url": verify_url,
        "caption": caption,
        "hashtags": hashtags,
        "company_page": SASHA_LINKEDIN_PAGE,
        "company_handle": SASHA_LINKEDIN_HANDLE,
        "og_title": og_title,
        "og_description": og_description,
    }


def _cached_png_dimensions(certificate) -> tuple:
    """(width, height) of the cached certificate PNG, read straight from the
    IHDR chunk. Falls back to the renderer's nominal output (the 1200x850 card
    at the 1.5x device scale factor) when the image hasn't been rendered yet."""
    default = (1800, 1275)
    try:
        import os
        import struct

        path = CertificateService._png_cache_path(certificate)
        if not os.path.exists(path):
            return default
        with open(path, "rb") as f:
            header = f.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return default
        width, height = struct.unpack(">II", header[16:24])
        return (width, height) if width and height else default
    except Exception:
        return default


def _load_certificate_for_share(cert_id: str, cert_hash: str, db: Session):
    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.secure_certificate_id == cert_id,
        IssuedCertificate.certificate_hash == cert_hash,
    ).first()
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )
    student = db.query(User).filter(User.id == certificate.user_id).first()
    course = db.query(Course).filter(Course.id == certificate.course_id).first()
    return certificate, student, course


@router.get("/share-meta/{cert_id}/{cert_hash}")
async def certificate_share_meta(
    cert_id: str,
    cert_hash: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Share payload for the in-app "Share on LinkedIn" dialog: the public share
    URL, the certificate image, and the personalised caption. Public, like the
    other certificate endpoints — a certificate is a shareable credential.
    """
    certificate, student, course = _load_certificate_for_share(cert_id, cert_hash, db)
    payload = _build_share_payload(certificate, student, course, request)

    from urllib.parse import quote

    payload["linkedin_share_url"] = (
        "https://www.linkedin.com/feed/?shareActive=true&text="
        + quote(payload["caption"], safe="")
    )
    payload["linkedin_fallback_url"] = (
        "https://www.linkedin.com/sharing/share-offsite/?url="
        + quote(payload["share_url"], safe="")
    )
    return payload


@router.get("/share/{cert_id}/{cert_hash}")
async def certificate_share_page(
    cert_id: str,
    cert_hash: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Public, crawlable landing page for a shared certificate.

    This is the URL that goes into the LinkedIn post. Its Open Graph image is
    the rendered certificate PNG, which is what makes LinkedIn show the
    certificate as the post preview instead of the site logo.
    """
    from fastapi.responses import HTMLResponse
    import html as html_lib

    certificate, student, course = _load_certificate_for_share(cert_id, cert_hash, db)
    meta = _build_share_payload(certificate, student, course, request)

    # Warm the PNG cache after the response is sent, so the crawler's og:image
    # fetch (which follows within seconds) hits a cached file rather than
    # waiting on a headless-Chrome render.
    def _warm_image():
        try:
            CertificateService.get_or_render_html_png(certificate)
        except Exception:
            pass

    background_tasks.add_task(_warm_image)

    img_width, img_height = _cached_png_dimensions(certificate)
    e = html_lib.escape
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(meta['og_title'])}</title>
<meta name="description" content="{e(meta['og_description'])}">

<meta property="og:type" content="article">
<meta property="og:site_name" content="SashaInfinity">
<meta property="og:title" content="{e(meta['og_title'])}">
<meta property="og:description" content="{e(meta['og_description'])}">
<meta property="og:image" content="{e(meta['image_url'])}">
<meta property="og:image:secure_url" content="{e(meta['image_url'])}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="{img_width}">
<meta property="og:image:height" content="{img_height}">
<meta property="og:image:alt" content="Certificate of completion awarded to {e(meta['student_name'])}">
<meta property="og:url" content="{e(meta['share_url'])}">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(meta['og_title'])}">
<meta name="twitter:description" content="{e(meta['og_description'])}">
<meta name="twitter:image" content="{e(meta['image_url'])}">

<link rel="canonical" href="{e(meta['share_url'])}">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px 16px; background: #f6f7f9; color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .card {{
    max-width: 960px; margin: 0 auto; background: #fff; border-radius: 16px;
    box-shadow: 0 10px 40px rgba(15, 23, 42, 0.08); overflow: hidden;
  }}
  .bar {{
    background: #E8701A; color: #fff; padding: 14px 24px;
    font-weight: 600; letter-spacing: .02em;
  }}
  .cert {{ display: block; width: 100%; height: auto; background: #fff; }}
  .body {{ padding: 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 6px; }}
  p {{ margin: 0 0 12px; color: #475569; line-height: 1.6; font-size: 15px; }}
  .meta {{ font-size: 13px; color: #64748b; }}
  .actions {{ margin-top: 20px; display: flex; gap: 12px; flex-wrap: wrap; }}
  a.btn {{
    display: inline-block; padding: 11px 20px; border-radius: 9px;
    text-decoration: none; font-weight: 600; font-size: 14px;
  }}
  .primary {{ background: #E8701A; color: #fff; }}
  .ghost {{ background: #f1f5f9; color: #0f172a; }}
  code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
</style>
</head>
<body>
  <div class="card">
    <div class="bar">Verified Certificate · SashaInfinity</div>
    <img class="cert" src="{e(meta['image_url'])}" alt="Certificate of completion awarded to {e(meta['student_name'])}">
    <div class="body">
      <h1>{e(meta['student_name'])} completed {e(meta['course_title'])}</h1>
      <p>{e(meta['og_description'])}</p>
      <p class="meta">Certificate ID: <code>{e(meta['certificate_id'])}</code></p>
      <div class="actions">
        <a class="btn primary" href="{e(meta['verify_url'])}">Verify this certificate</a>
        <a class="btn ghost" href="https://sashainfinity.com/courses">Explore courses at SashaInfinity</a>
      </div>
    </div>
  </div>
</body>
</html>"""

    return HTMLResponse(content=page, headers={"Cache-Control": "public, max-age=600"})


@router.get("/download-html-pdf/{cert_id}/{cert_hash}")
async def download_certificate_html_pdf(
    cert_id: str,
    cert_hash: str,
    db: Session = Depends(get_db)
):
    """
    Download certificate PDF rendered from the HTML template (the same
    "Certificate of Excellence" design shown in the on-screen preview /
    verify page), via headless Chrome. Falls back to the ReportLab design
    only if Chrome rendering fails.

    The URL may end in `.pdf` — that extension is what lets Cloudflare cache
    the response instead of fetching all 412KB from origin on every download.
    """
    import asyncio

    cert_hash, _ = split_asset_ext(cert_hash, _PDF_EXTENSIONS)

    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.secure_certificate_id == cert_id,
        IssuedCertificate.certificate_hash == cert_hash
    ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    # Render the HTML template to PDF (blocking Chrome call → threadpool).
    pdf_content = await asyncio.to_thread(
        CertificateService.get_or_render_html_pdf, certificate
    )

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{cert_id}.pdf",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/download-pdf/{cert_id}/{cert_hash}")
async def download_certificate_public(
    cert_id: str,
    cert_hash: str,
    db: Session = Depends(get_db)
):
    """
    Public PDF download using secure certificate ID and hash
    Accessible via /api/v1/certificates/download-pdf/{cert_id}/{cert_hash}

    Renders the HTML template design (matching the on-screen preview) via
    headless Chrome so every download path returns the same certificate.

    The URL may end in `.pdf` so Cloudflare will edge-cache the response.
    """
    import asyncio

    cert_hash, _ = split_asset_ext(cert_hash, _PDF_EXTENSIONS)

    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.secure_certificate_id == cert_id,
        IssuedCertificate.certificate_hash == cert_hash
    ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    pdf_content = await asyncio.to_thread(
        CertificateService.get_or_render_html_pdf, certificate
    )
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificate_{cert_id}.pdf",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/public-url/{certificate_id}")
async def get_public_certificate_url(
    certificate_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public: resolve a certificate by its numeric ID and return its public
    verification/share URLs (Issue 4).

    The certificate's own identity — its DB id, secure_certificate_id, and
    certificate_hash — is enough to build every public link (verification
    page, OG share page, image, PDF). This endpoint is the canonical
    "ID-based public link" lookup so admins/students can share a credential
    by a single short ID instead of the raw hash.

    Registered BEFORE the catch-all `/{certificate_id}` route so FastAPI
    matches it instead of treating "public-url" as a certificate id.
    No auth: this only returns data already public on the verify page.
    """
    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.id == certificate_id
    ).first()
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    base_url = _public_base_url(request)
    secure_id = certificate.secure_certificate_id or ""
    cert_hash = certificate.certificate_hash or ""

    return {
        "certificate_id": certificate.id,
        "secure_certificate_id": secure_id,
        "verification_hash": cert_hash,
        "public_url": f"{base_url}/verify-certificate/{cert_hash}" if cert_hash else "",
        "share_url": f"{base_url}/api/v1/certificates/share/{secure_id}/{cert_hash}" if secure_id and cert_hash else "",
        "certificate_url": certificate_download_url(certificate),
        "image_url": f"/api/v1/certificates/image/{secure_id}/{cert_hash}.webp" if secure_id and cert_hash else "",
    }


@router.get("/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific certificate details (must come AFTER all specific multi-segment routes)
    """
    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.id == certificate_id,
        IssuedCertificate.user_id == current_user.id
    ).first()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    return {
        "id": certificate.id,
        "course_id": certificate.course_id,
        "course_title": certificate.course.post_title,
        "student_name": current_user.display_name,
        "instructor_name": certificate.course.instructor.display_name,
        "completion_date": certificate.completion_date,
        "certificate_url": certificate_download_url(certificate),
        "verification_code": certificate.certificate_hash,
        "issued_at": certificate.created_at,
        # Issue 4: ID-based public verification link.
        "secure_certificate_id": certificate.secure_certificate_id or "",
        "public_url": (
            f"/verify-certificate/{certificate.certificate_hash}"
            if certificate.certificate_hash else ""
        ),
    }

@router.get("/verify/{verification_code}")
async def verify_certificate(
    verification_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify certificate authenticity (public endpoint)
    Returns JSON with certificate details
    """
    from app.models.certificate import CertificateVerification
    from datetime import datetime

    # Get client info for logging
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    certificate = db.query(IssuedCertificate).filter(
        IssuedCertificate.certificate_hash == verification_code
    ).first()

    if not certificate:
        # Log failed verification attempt
        failed_verification = CertificateVerification(
            certificate_id=None,  # Unknown certificate
            certificate_hash=verification_code,
            verified_by_ip=client_ip,
            verified_by_user_agent=user_agent,
            verification_result="invalid"
        )
        db.add(failed_verification)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found or invalid verification code"
        )

    # Log successful verification
    verification_log = CertificateVerification(
        certificate_id=certificate.id,
        certificate_hash=verification_code,
        verified_by_ip=client_ip,
        verified_by_user_agent=user_agent,
        verification_result="valid"
    )
    db.add(verification_log)
    db.commit()

    return {
        "valid": True,
        "certificate_id": certificate.certificate_hash,
        "student_name": certificate.student.display_name,
        "student_email": certificate.student.user_email,
        "course_title": certificate.course.post_title,
        "course_description": certificate.course.post_content[:200] if certificate.course.post_content else "",
        "instructor_name": certificate.course.instructor.display_name,
        "completion_date": certificate.completion_date,
        "issue_date": certificate.created_at,
        "progress": float(certificate.course_completion_percentage),
        "course_level": "intermediate",  # TODO: Get from course metadata
        "verified_at": datetime.utcnow(),
        "certificate_url": certificate_download_url(certificate),
        "verification_message": f"This certificate was issued to {certificate.student.display_name} upon successful completion of {certificate.course.post_title}."
    }



# Certificate Template Management (Instructor/Admin)

@router.get("/templates/", response_model=List[CertificateTemplateResponse])
async def get_certificate_templates(
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Get certificate templates (instructor/admin only).

    DEPRECATED (Task 6): superseded by the richer instructor designer API at
    /api/v1/certificates/designer (elements_config CRUD, global-template
    visibility, delete-blocked-when-referenced, preview rendering). This
    primitive `content`-string CRUD is kept for backward compatibility only
    — do not build new instructor UI against it.
    """
    if current_user.role == "admin":
        templates = db.query(Certificate).all()
    else:
        templates = db.query(Certificate).filter(
            Certificate.post_author == current_user.id
        ).all()

    return [
        {
            "id": template.id,
            "name": template.post_title,
            "description": template.post_excerpt,
            "template_data": {"content": template.post_content},
            "is_default": False,
            "created_by": template.post_author,
            "created_at": template.created_at
        }
        for template in templates
    ]

@router.post("/templates/", response_model=CertificateTemplateResponse)
async def create_certificate_template(
    template_data: CertificateTemplateCreate,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Create new certificate template.

    DEPRECATED (Task 6): use POST /api/v1/certificates/designer instead —
    this endpoint only stores a raw HTML `content` string, not the
    elements_config design the production render path (and every current
    template gallery) actually consumes. Kept for backward compatibility.
    """
    new_template = Certificate(
        post_title=template_data.name,
        post_excerpt=template_data.description,
        post_content=template_data.template_data.get("content", ""),
        post_author=current_user.id,
        post_status="publish",
        post_type="tutor_certificates"
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    return {
        "id": new_template.id,
        "name": new_template.post_title,
        "description": new_template.post_excerpt,
        "template_data": {"content": new_template.post_content},
        "is_default": False,
        "created_by": new_template.post_author,
        "created_at": new_template.created_at
    }

@router.put("/templates/{template_id}")
async def update_certificate_template(
    template_id: int,
    template_data: CertificateTemplateCreate,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Update certificate template.

    DEPRECATED (Task 6): use PUT /api/v1/certificates/designer/{id} instead.
    Kept for backward compatibility.
    """
    template = db.query(Certificate).filter(
        Certificate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check permissions
    if current_user.role != "admin" and template.post_author != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this template"
        )

    # Update template
    template.post_title = template_data.name
    template.post_excerpt = template_data.description
    template.post_content = template_data.template_data.get("content", "")

    db.commit()

    return {"message": "Template updated successfully"}

@router.delete("/templates/{template_id}")
async def delete_certificate_template(
    template_id: int,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Delete certificate template.

    DEPRECATED (Task 6): use DELETE /api/v1/certificates/designer/{id}
    instead — that endpoint also blocks deletion while a course or issued
    certificate still references the template (409), which this legacy
    route does not check at all. Kept for backward compatibility.
    """
    template = db.query(Certificate).filter(
        Certificate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check permissions
    if current_user.role != "admin" and template.post_author != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this template"
        )

    # Cannot delete templates with ID <= 3 (reserved default templates)
    if template.id <= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default template"
        )

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}

@router.get("/templates/list")
async def list_certificate_templates(
    db: Session = Depends(get_db)
):
    """Get all certificate templates - public for course selection.

    Includes both the 5 legacy hand-authored (post_name slug) designs AND
    ready builder templates (a Certificate row with elements_config) — the
    course editor's template picker must offer both (spec Task 6 binding).

    PUBLIC/anonymous endpoint — scoped to (post_name is a non-empty legacy
    slug) OR (is_global = true). A row with neither is an instructor's own,
    non-global elements_config draft (created via POST /certificates/
    designer) and must NOT be exposed here (fix round M-1: this endpoint
    previously selected every post_status='publish' row unconditionally,
    which leaked every instructor's private draft — name, layout, background
    image URL — to any anonymous caller).
    """
    from sqlalchemy import text
    rows = db.execute(text("""
        SELECT id, post_title, post_name, background_color, title_font_color, title_font_family,
               body_font_family, certificate_orientation, elements_config, background_image
        FROM certificates
        WHERE post_status='publish'
          AND (TRIM(COALESCE(post_name, '')) != '' OR is_global = true)
        ORDER BY id
    """)).fetchall()

    def _thumb(template_id, slug, elements_config, background_image):
        # Preview image served from the /certificate-files static mount for
        # the legacy hand-authored designs. A builder (elements_config)
        # template checks for a real Chrome-rendered thumbnail first (Task 8
        # fix round D-8: seed_designer_templates.py writes these to
        # certificates/thumbnails/designer-{id}.png when Chrome is
        # available — see designer_thumbnail_url()), then falls back to its
        # own background image when it has one, so the picker shows
        # something representative rather than a generic/unrelated legacy
        # thumbnail.
        s = (slug or "").strip()
        if s:
            return f"/certificate-files/thumbnails/{s}.png"
        if elements_config:
            from app.routers.certificate_designer import designer_thumbnail_url
            rendered = designer_thumbnail_url(template_id)
            if rendered:
                return rendered
            if background_image:
                return background_image
            return None
        return "/certificate-files/thumbnails/default.png"

    def _has_elements(raw) -> bool:
        if not raw:
            return False
        try:
            import json as _json
            parsed = _json.loads(raw) if isinstance(raw, str) else raw
            return bool(parsed)
        except Exception:
            return bool(raw)

    return [{"id": r.id, "name": r.post_title, "slug": (r.post_name or "").strip(),
             "thumbnail": _thumb(r.id, r.post_name, r.elements_config, r.background_image),
             "template_type": "builder" if _has_elements(r.elements_config) and not (r.post_name or "").strip() else "legacy",
             "bg_color": r.background_color,
             "title_color": r.title_font_color, "font": r.title_font_family,
             "body_font": r.body_font_family,
             "orientation": r.certificate_orientation} for r in rows]


# ---------------------------------------------------------------------------
# Admin manual certificate release / revocation
# ---------------------------------------------------------------------------

class AdminIssueIn(BaseModel):
    force_completion: bool = False


class AdminRevokeIn(BaseModel):
    reason: str


@router.post("/admin/enrollments/{enrollment_id}/issue")
async def admin_issue_certificate_for_enrollment(
    enrollment_id: int,
    payload: AdminIssueIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin manual issue — optionally forces completion first then calls
    the central idempotent helper."""
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    if enrollment.completion_date is None:
        if not payload.force_completion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enrollment is not completed. Pass force_completion=true to override.",
            )
        try:
            enrollment.completion_date = datetime.now(timezone.utc)
            enrollment.course_progress_percentage = 100
            enrollment.enrollment_status = "completed"
            db.commit()
            db.refresh(enrollment)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to force completion: {exc}",
            )

    cert, newly_issued = CertificateService.issue_certificate_for_enrollment(db, enrollment)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to issue certificate",
        )

    return {
        "certificate_id": cert.id,
        "newly_issued": bool(newly_issued),
        "certificate_url": certificate_download_url(cert),
        "verification_code": cert.certificate_hash,
        "completion_date": cert.completion_date,
    }


@router.post("/admin/{issued_cert_id}/revoke")
async def admin_revoke_certificate(
    issued_cert_id: int,
    payload: AdminRevokeIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin revoke — marks cert invalid and unlinks from enrollment.
    Row is preserved for audit trail."""
    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason is required")

    cert = db.query(IssuedCertificate).filter(IssuedCertificate.id == issued_cert_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    try:
        cert.is_valid = False
        cert.invalidated_date = datetime.now(timezone.utc)
        cert.invalidation_reason = reason

        # Unlink from the enrollment (so "completed but no cert" is visible).
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == cert.user_id,
                Enrollment.course_id == cert.course_id,
            )
            .first()
        )
        if enrollment:
            enrollment.certificate_id = None
            enrollment.certificate_url = None

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke certificate: {exc}",
        )

    return {
        "ok": True,
        "certificate_id": cert.id,
        "is_valid": False,
        "invalidation_reason": reason,
        "invalidated_date": cert.invalidated_date,
    }
