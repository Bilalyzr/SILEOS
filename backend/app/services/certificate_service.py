"""
Certificate Service - PDF generation using ReportLab
Matches the orange Certificate of Completion template
"""
import os, uuid, secrets, base64, io, logging, threading
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.exc import IntegrityError
from PIL import Image
import qrcode
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)


def assignments_all_approved(all_assignment_ids: set, graded_assignment_ids: set) -> bool:
    """True if every assignment id has a graded (approved) submission.

    Pure/DB-free so it is unit-testable. No assignments -> trivially True.
    """
    return set(all_assignment_ids).issubset(set(graded_assignment_ids))


def course_assignments_approved(db, user_id: int, course_id: int) -> bool:
    """True if every assignment in the course has a GRADED submission by the user.

    Courses with no assignments return True (nothing to approve).
    """
    from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
    all_ids = {row.id for row in db.query(Assignment.id).filter(
        Assignment.course_id == course_id).all()}
    if not all_ids:
        return True
    graded_ids = {row.assignment_id for row in db.query(AssignmentSubmission.assignment_id).filter(
        AssignmentSubmission.user_id == user_id,
        AssignmentSubmission.assignment_id.in_(all_ids),
        AssignmentSubmission.status == SubmissionStatus.GRADED,
    ).all()}
    return assignments_all_approved(all_ids, graded_ids)

def course_completion_percentages(db, user_id: int, course_id: int) -> Tuple[float, float]:
    """(quiz_pct, assignment_pct) completion breakdown for a certificate row.

    Same counting rules as CourseService.calculate_course_progress
    (literally — both call CourseService.passed_distinct_quizzes):
      * quizzes — DISTINCT quizzes with a passing ended attempt
        (percentage >= quiz.quiz_passing_grade);
      * assignments — assignments with a GRADED submission
        (mirrors course_assignments_approved).
    A content type the course has none of yields 0.0 (never a divide-by-zero).
    """
    from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
    from app.services.course_service import CourseService

    passed_quiz_ids, total_quizzes = CourseService.passed_distinct_quizzes(
        db, user_id, course_id
    )
    quiz_pct = (
        min(100.0, len(passed_quiz_ids) / total_quizzes * 100)
        if total_quizzes
        else 0.0
    )

    all_assignment_ids = {row.id for row in db.query(Assignment.id).filter(
        Assignment.course_id == course_id).all()}
    assignment_pct = 0.0
    if all_assignment_ids:
        graded_ids = {row.assignment_id for row in db.query(AssignmentSubmission.assignment_id).filter(
            AssignmentSubmission.user_id == user_id,
            AssignmentSubmission.assignment_id.in_(all_assignment_ids),
            AssignmentSubmission.status == SubmissionStatus.GRADED,
        ).all()}
        assignment_pct = min(
            100.0, len(all_assignment_ids & graded_ids) / len(all_assignment_ids) * 100
        )

    return quiz_pct, assignment_pct


class CertificateService:

    # Cap concurrent headless-Chrome renders so a burst of certificate
    # downloads can't spawn dozens of Chrome processes at once and exhaust the
    # container's memory / process table.
    _render_semaphore = threading.Semaphore(2)

    # Where the Dockerfile pins ChromeDriver. When it exists we hand it to
    # Selenium explicitly instead of letting Selenium Manager resolve a driver,
    # which it does by downloading one at request time — a step that needs
    # outbound network access from this container and is the usual reason
    # renders fail in a locked-down deployment.
    _CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"

    @staticmethod
    def _build_chrome_driver(opts):
        """Construct a headless Chrome driver, preferring the pinned binary."""
        from selenium import webdriver

        if os.path.exists(CertificateService._CHROMEDRIVER_PATH):
            from selenium.webdriver.chrome.service import Service

            return webdriver.Chrome(
                service=Service(executable_path=CertificateService._CHROMEDRIVER_PATH),
                options=opts,
            )

        logger.warning(
            "No pinned chromedriver at %s — falling back to Selenium Manager, "
            "which must download a driver and therefore needs outbound network access",
            CertificateService._CHROMEDRIVER_PATH,
        )
        return webdriver.Chrome(options=opts)

    # ------------------------------------------------------------------
    # elements_config unification (Task 6): the builder's saved design is
    # now the REAL production render path, not just a preview. A Certificate
    # row with a non-empty elements_config is rendered dynamically from
    # certificate_html_renderer.build_certificate_html; a row with a
    # post_name slug (the 5 legacy hand-authored designs) keeps using the
    # existing file-based template path untouched — resolve_template_path in
    # routers/certificates.py still owns that lookup and is unchanged.
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_certificate_template_row(db, issued_cert):
        """Return the Certificate template row for an issued certificate, or
        None if it cannot be resolved. Never raises."""
        try:
            from app.models.certificate import Certificate as _CertTemplate

            template_id = getattr(issued_cert, "certificate_id", None)
            if not template_id:
                return None
            return db.query(_CertTemplate).filter(_CertTemplate.id == template_id).first()
        except Exception:
            return None

    @staticmethod
    def template_uses_elements_config(template) -> bool:
        """True when a Certificate row should render via the dynamic
        elements_config HTML path rather than the legacy hand-authored file.

        A row qualifies only when it has a non-empty elements_config AND no
        post_name slug — a slug means it's one of the 5 legacy designs, which
        must keep resolving to their existing file (spec C1 regression
        guard), even if elements_config happens to be populated too.
        """
        if template is None:
            return False
        elements = getattr(template, "elements_config", None)
        slug = (getattr(template, "post_name", "") or "").strip()
        return bool(elements) and not slug

    @staticmethod
    def build_certificate_html_for_issued(db, issued_cert, base_url: Optional[str] = None) -> Optional[str]:
        """Build the elements_config-rendered HTML document for an issued
        certificate, or None when the certificate's template doesn't use the
        elements_config path (caller should fall back to the legacy file).
        """
        template = CertificateService.resolve_certificate_template_row(db, issued_cert)
        if not CertificateService.template_uses_elements_config(template):
            return None

        from app.core.config import get_settings
        from app.models.course import Course
        from app.models.user import User
        from app.services.certificate_html_renderer import build_certificate_html

        settings = get_settings()
        frontend_base = (base_url or getattr(settings, "FRONTEND_URL", "https://lms.sashainfinity.com")).rstrip("/")

        student = db.query(User).filter(User.id == issued_cert.user_id).first()
        course = db.query(Course).filter(Course.id == issued_cert.course_id).first()

        completion_date = issued_cert.completion_date
        date_text = completion_date.strftime("%B %d, %Y") if completion_date else ""
        cert_id_display = f"CERT-{(completion_date or datetime.now(timezone.utc)).year}-{str(issued_cert.id).zfill(6)}"
        verify_url = f"{frontend_base}/verify-certificate/{issued_cert.certificate_hash}"

        values = {
            "student_name": student.display_name if student else "Student",
            "course_name": course.post_title if course else "Course",
            "completion_date": date_text,
            "certificate_id": cert_id_display,
            "instructor_name": (
                course.instructor.display_name
                if course and getattr(course, "instructor", None)
                else "SashaInfinity"
            ),
            "verify_url": verify_url,
        }
        return build_certificate_html(template, values)

    @staticmethod
    def _generate_qr_code_img(data: str):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    @staticmethod
    def generate_verification_code() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def generate_secure_certificate_id(user_id: int, course_id: int, issue_date) -> str:
        import hashlib
        data = f"{user_id}-{course_id}-{issue_date}-{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()[:20].upper()

    @staticmethod
    def generate_secure_verification_url(base_url: str, certificate_hash: str, certificate_id: str = "") -> str:
        # Public "certified" link: the frontend verification portal reads the
        # hash as a PATH param (route /verify-certificate/:certificateId) and
        # looks the certificate up by certificate_hash. `certificate_id` is
        # kept for signature compatibility but is no longer part of the URL.
        return f"{base_url.rstrip('/')}/verify-certificate/{certificate_hash}"

    @staticmethod
    async def generate_certificate(certificate_data: Dict[str, Any]) -> str:
        cert_dir = "certificates"
        os.makedirs(cert_dir, exist_ok=True)
        filename = f"certificate_{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(cert_dir, filename)
        CertificateService._generate_pdf(certificate_data, file_path)
        return f"/certificate-files/{filename}"

    @staticmethod
    def _generate_pdf(data: Dict[str, Any], file_path: str):
        from app.core.config import get_settings
        settings = get_settings()

        student_name = data.get("student_name", "Student Name")
        course_title = data.get("course_title", "Course Title")
        instructor_name = data.get("instructor_name", "Instructor")
        completion_date = data.get("completion_date", datetime.now())
        certificate_id = data.get("certificate_id", "0")
        certificate_hash = data.get("certificate_hash", "")
        base_url = data.get("base_url", getattr(settings, "FRONTEND_URL", "https://lms.sashainfinity.com"))

        if isinstance(completion_date, str):
            date_text = completion_date
        else:
            date_text = completion_date.strftime("%B %d, %Y")

        # Public verification portal link — hash is a PATH param, matching the
        # frontend route /verify-certificate/:certificateId (looked up by hash).
        verification_url = f"{base_url.rstrip('/')}/verify-certificate/{certificate_hash}"

        # Page setup - landscape A4
        W, H = landscape(A4)  # 841.89 x 595.28 pts
        c = canvas.Canvas(file_path, pagesize=landscape(A4))

        # ── LEFT PANEL (orange) ──────────────────────────────
        panel_w = W * 0.32
        c.setFillColor(colors.HexColor("#E8701A"))
        c.rect(0, 0, panel_w, H, fill=1, stroke=0)

        # Left panel teal accent strip
        c.setFillColor(colors.HexColor("#1A7A8A"))
        c.rect(panel_w - 8, 0, 8, H, fill=1, stroke=0)

        # "Certificate" text on left
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(panel_w / 2, H - 120, "Certificate")
        c.setFont("Helvetica", 20)
        c.drawCentredString(panel_w / 2, H - 150, "of")
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(panel_w / 2, H - 178, "Completion")

        # QR code on left panel
        qr_buf = CertificateService._generate_qr_code_img(verification_url)
        qr_img = Image.open(qr_buf)
        qr_path = f"/tmp/qr_{uuid.uuid4().hex}.png"
        qr_img.save(qr_path)
        qr_size = 90
        c.drawImage(qr_path, (panel_w - qr_size) / 2, 80, qr_size, qr_size)
        os.remove(qr_path)

        # Decorative circles on left
        c.setFillColor(colors.HexColor("#1A7A8A"))
        c.circle(panel_w / 2, H * 0.45, 55, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#E8701A"))
        c.circle(panel_w / 2, H * 0.45, 48, fill=1, stroke=0)
        c.setStrokeColor(colors.white)
        c.setLineWidth(2)
        c.circle(panel_w / 2, H * 0.45, 52, fill=0, stroke=1)
        # SI text in circle
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(panel_w / 2, H * 0.45 - 8, "SI")

        # ── RIGHT PANEL (cream/white) ─────────────────────────
        rx = panel_w + 10  # right area x start

        # Top logo area - company name
        c.setFillColor(colors.HexColor("#E8701A"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(rx + 20, H - 50, "SashaInfinity")
        c.setFillColor(colors.HexColor("#666666"))
        c.setFont("Helvetica", 9)
        c.drawString(rx + 20, H - 64, "Premium Technology Education")

        # Orange seal circle top right
        c.setFillColor(colors.HexColor("#E8701A"))
        c.circle(W - 60, H - 55, 38, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(W - 60, H - 52, "VERIFIED")
        c.setFont("Helvetica", 7)
        c.drawCentredString(W - 60, H - 63, "CERTIFICATE")

        # Divider line
        c.setStrokeColor(colors.HexColor("#DDDDDD"))
        c.setLineWidth(1)
        c.line(rx + 20, H - 80, W - 20, H - 80)

        # "This is to certify that" 
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 10)
        c.drawString(rx + 20, H - 110, "This is to certify that")

        # Student name - large
        c.setFillColor(colors.HexColor("#222222"))
        c.setFont("Helvetica-Bold", 32)
        c.drawString(rx + 20, H - 155, student_name)

        # Underline for student name
        name_w = c.stringWidth(student_name, "Helvetica-Bold", 32)
        c.setStrokeColor(colors.HexColor("#E8701A"))
        c.setLineWidth(2)
        c.line(rx + 20, H - 165, rx + 20 + min(name_w, W - rx - 60), H - 165)

        # "has successfully completed the course"
        c.setFillColor(colors.HexColor("#666666"))
        c.setFont("Helvetica", 11)
        c.drawString(rx + 20, H - 195, "has successfully completed the course")

        # Course title
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 16)
        # Wrap long course titles
        max_w = W - rx - 60
        if c.stringWidth(course_title, "Helvetica-Bold", 16) > max_w:
            words = course_title.split()
            line1, line2 = "", ""
            for w in words:
                test = line1 + " " + w if line1 else w
                if c.stringWidth(test, "Helvetica-Bold", 16) < max_w:
                    line1 = test
                else:
                    line2 = (line2 + " " + w).strip()
            c.drawString(rx + 20, H - 225, line1)
            if line2:
                c.drawString(rx + 20, H - 245, line2)
                bottom_y = H - 245
            else:
                bottom_y = H - 225
        else:
            c.drawString(rx + 20, H - 225, course_title)
            bottom_y = H - 225

        # Date
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 9)
        c.drawString(rx + 20, bottom_y - 30, f"Completed on: {date_text}")

        # ── SIGNATURE SECTION ──────────────────────────────────
        sig_y = 100

        # Instructor name
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(rx + 20, sig_y + 30, instructor_name)
        c.setStrokeColor(colors.HexColor("#333333"))
        c.setLineWidth(1)
        c.line(rx + 20, sig_y + 22, rx + 180, sig_y + 22)
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 9)
        c.drawString(rx + 20, sig_y + 8, "Instructor, SashaInfinity")

        # Verification ID bottom right
        cert_short = str(certificate_id).zfill(6)
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 8)
        c.drawRightString(W - 20, sig_y + 8, f"Certificate ID: CERT-{datetime.now().year}-{cert_short}")
        c.drawRightString(W - 20, sig_y - 5, verification_url[:60] + "..." if len(verification_url) > 60 else verification_url)

        # Bottom border line
        c.setStrokeColor(colors.HexColor("#E8701A"))
        c.setLineWidth(3)
        c.line(panel_w + 8, 15, W - 15, 15)

        c.save()

    # ------------------------------------------------------------------
    # Builder-template rendering (honors the admin-designed layout)
    # ------------------------------------------------------------------
    @staticmethod
    def _map_font(family: Optional[str], weight: Optional[str]) -> str:
        """Map a builder font family + weight onto a ReportLab base-14 font."""
        fam = (family or "Helvetica").lower()
        bold = str(weight or "").lower() in ("bold", "600", "700", "800", "900")
        if "times" in fam or "georgia" in fam or "serif" in fam:
            return "Times-Bold" if bold else "Times-Roman"
        if "courier" in fam or "mono" in fam:
            return "Courier-Bold" if bold else "Courier"
        return "Helvetica-Bold" if bold else "Helvetica"

    @staticmethod
    def _load_image_reader(url: Optional[str]):
        """Best-effort load of an image (data URI, http(s) URL, or local /uploads
        style path) into a ReportLab ImageReader. Returns None on any failure so a
        missing asset never hard-fails preview rendering."""
        if not url:
            return None
        from reportlab.lib.utils import ImageReader
        try:
            if url.startswith("data:"):
                _, _, b64 = url.partition(",")
                return ImageReader(io.BytesIO(base64.b64decode(b64)))
            if url.startswith("http://") or url.startswith("https://"):
                import requests
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                return ImageReader(io.BytesIO(resp.content))
            # Local / relative path served under /uploads or /certificate-files.
            clean = url.lstrip("/")
            candidates = [url, clean]
            for base in ("/app", os.getcwd()):
                candidates.append(os.path.join(base, clean))
            # /certificate-files/* is served from the ./certificates dir.
            if clean.startswith("certificate-files/"):
                rel = clean[len("certificate-files/"):]
                for base in ("/app/certificates", os.path.join(os.getcwd(), "certificates")):
                    candidates.append(os.path.join(base, rel))
            for path in candidates:
                if path and os.path.isfile(path):
                    return ImageReader(path)
        except Exception:
            logger.warning("certificate preview: could not load image %s", url, exc_info=True)
        return None

    @staticmethod
    def render_image_pdf(image_ref: Optional[str], file_path: str) -> bool:
        """Wrap a single image (an uploaded template, or a hand-authored design's
        pre-rendered thumbnail) into a one-page PDF sized to the image.

        Lets image-based templates preview through the very same
        `application/pdf` viewer the admin UI already uses for rendered
        templates — so the fix needs no frontend change. Returns False if the
        image cannot be loaded, letting the caller fall back gracefully.
        """
        img = CertificateService._load_image_reader(image_ref)
        if img is None:
            return False
        try:
            iw, ih = img.getSize()
        except Exception:
            iw, ih = (0, 0)
        if not iw or not ih:
            iw, ih = (1123, 794)
        try:
            c = canvas.Canvas(file_path, pagesize=(iw, ih))
            c.drawImage(img, 0, 0, width=iw, height=ih, mask="auto")
            c.save()
            return True
        except Exception:
            logger.warning("certificate preview: image->pdf wrap failed for %s", image_ref, exc_info=True)
            return False

    @staticmethod
    def render_template_preview(template: Dict[str, Any], sample: Dict[str, str], file_path: str):
        """Render a *builder* certificate template (its background + positioned
        elements) to a PDF, so the admin preview shows the actual design that was
        saved — not the hardcoded default certificate.

        `template` carries the shape returned by the admin list endpoint:
        {dimensions:{width,height}, background:{type,value,image_url}, elements:[...]}.
        Coordinates are in the builder's top-left pixel space; we render the page
        at those pixel dimensions (px treated as points) and flip Y for ReportLab's
        bottom-up axis so positions match the on-screen canvas 1:1.
        """
        dims = template.get("dimensions") or {}
        W = float(dims.get("width") or 1123)
        H = float(dims.get("height") or 794)
        background = template.get("background") or {}
        elements = template.get("elements") or []

        c = canvas.Canvas(file_path, pagesize=(W, H))

        # ── Background ────────────────────────────────────────
        if background.get("type") == "image" and background.get("image_url"):
            img = CertificateService._load_image_reader(background.get("image_url"))
            if img is not None:
                try:
                    c.drawImage(img, 0, 0, width=W, height=H,
                                preserveAspectRatio=False, mask="auto")
                except Exception:
                    logger.warning("certificate preview: bg image draw failed", exc_info=True)
        else:
            try:
                c.setFillColor(colors.HexColor(background.get("value") or "#ffffff"))
            except Exception:
                c.setFillColor(colors.white)
            c.rect(0, 0, W, H, fill=1, stroke=0)

        def _text_for(el: Dict[str, Any]) -> str:
            t = el.get("type")
            if t == "student_name":
                return sample.get("student_name") or sample.get("student_name", "Student Name")
            if t == "course_name":
                return sample.get("course_name") or sample.get("course_title", "Course Title")
            if t in ("date", "completion_date"):
                return sample.get("completion_date", "")
            if t == "certificate_id":
                return sample.get("certificate_id", "")
            if t == "instructor_name":
                return sample.get("instructor_name", "")
            if t == "text":
                return el.get("content") or ""
            return ""

        # ── Elements (respect z_index paint order) ────────────
        for el in sorted(elements, key=lambda e: e.get("z_index", 0)):
            etype = el.get("type")
            x = float(el.get("x", 0) or 0)
            y = float(el.get("y", 0) or 0)
            w = float(el.get("width", 0) or 0)
            h = float(el.get("height", 0) or 0)

            if etype in ("image", "signature", "signature_image", "logo"):
                # L-2: elements_config-originated image_url values may predate
                # write-time validation (routers/certificate_designer.
                # validate_elements_config) or arrive via another write path
                # (e.g. admin.py's certificate-templates-v2 PUT) — apply the
                # same same-origin-or-data-URI allowlist here before this
                # (ReportLab) fallback renderer touches it. _load_image_reader
                # itself is left untouched — render_image_pdf/background-image
                # callers below are pre-existing admin-only behavior out of
                # this task's scope.
                from app.services.certificate_html_renderer import is_safe_asset_src

                image_url = el.get("image_url")
                img = (
                    CertificateService._load_image_reader(image_url)
                    if is_safe_asset_src(image_url)
                    else None
                )
                if img is not None:
                    try:
                        c.drawImage(img, x, H - y - h, width=w, height=h,
                                    preserveAspectRatio=True, mask="auto")
                    except Exception:
                        logger.warning("certificate preview: element image draw failed", exc_info=True)
                continue

            if etype == "rect":
                fill = el.get("background_color") or el.get("fill")
                try:
                    if fill:
                        c.setFillColor(colors.HexColor(fill))
                        c.rect(x, H - y - h, w, h, fill=1, stroke=0)
                except Exception:
                    logger.warning("certificate preview: rect draw failed", exc_info=True)
                continue

            if etype == "line":
                color = el.get("font_color") or el.get("line_color") or "#000000"
                thickness = float(el.get("line_thickness") or 2)
                try:
                    c.setStrokeColor(colors.HexColor(color))
                    c.setLineWidth(thickness)
                    c.line(x, H - y, x + w, H - y)
                except Exception:
                    logger.warning("certificate preview: line draw failed", exc_info=True)
                continue

            if etype == "qr_code":
                # Feasible fallback: draw the QR (qrcode + PIL ImageReader)
                # for the same verify URL the HTML renderer would encode.
                verify_url = sample.get("verify_url") or ""
                if verify_url:
                    try:
                        from reportlab.lib.utils import ImageReader

                        qr_buf = CertificateService._generate_qr_code_img(verify_url)
                        c.drawImage(ImageReader(qr_buf), x, H - y - h, width=w, height=h, mask="auto")
                    except Exception:
                        logger.warning("certificate preview: qr draw failed", exc_info=True)
                continue

            text = _text_for(el)
            if not text:
                continue

            font_size = float(el.get("font_size") or 24)
            c.setFont(CertificateService._map_font(el.get("font_family"), el.get("font_weight")), font_size)
            try:
                c.setFillColor(colors.HexColor(el.get("font_color") or "#000000"))
            except Exception:
                c.setFillColor(colors.black)

            # Match the builder's flex box: text vertically centered in the element.
            baseline = H - y - (h / 2.0) - (font_size * 0.35)
            align = (el.get("text_align") or "left").lower()
            if align == "center":
                c.drawCentredString(x + w / 2.0, baseline, text)
            elif align == "right":
                c.drawRightString(x + w - 4, baseline, text)
            else:
                c.drawString(x + 4, baseline, text)

        c.save()

    @staticmethod
    def grant_internship_eligibility_on_certificate(db, user_id: int) -> None:
        """
        SS2 integration hook: when a certificate is issued to a user, ensure
        they have a CandidateEligibility row with source='auto_certificate'
        and eligible=True. Idempotent — safe to call multiple times.

        Never raises: eligibility is best-effort; certificate issuance must
        not fail because of a downstream bookkeeping error.
        """
        try:
            from app.models.candidate import CandidateEligibility  # local import
            existing = (
                db.query(CandidateEligibility)
                .filter(CandidateEligibility.user_id == user_id)
                .first()
            )
            if existing:
                # Don't downgrade a SPOC decision; just ensure eligible=True
                # for auto rows. Leave SPOC-owned rows untouched.
                if existing.source == "auto_certificate" and not existing.eligible:
                    existing.eligible = True
                    db.commit()
                return
            row = CandidateEligibility(
                user_id=user_id,
                source="auto_certificate",
                eligible=True,
                reason="Auto-granted on certificate issue",
            )
            db.add(row)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            # Swallow — see docstring.

    @staticmethod
    def issue_certificate_for_enrollment(db, enrollment) -> Tuple[Optional[object], bool]:
        """
        Idempotent, synchronous certificate issuance hook.

        Called from every site that can push an enrollment to 100% completion
        (mark-lesson-complete, video-watch save, quiz submit, assignment grade,
        and the explicit /certificates/generate endpoint).

        Behavior:
          * If the enrollment has no `completion_date`, does nothing and
            returns (existing_or_none, False). Callers are expected to have
            already run `CourseService.calculate_course_progress` which sets
            it when the course is truly complete.
          * If a VALID `IssuedCertificate` already exists for
            (user_id, course_id), returns (existing_row, False). No re-issue,
            no hook re-fire (`grant_internship_eligibility_on_certificate`
            is itself idempotent — safe if a caller re-fires it, but we
            avoid the extra query).
          * If an INVALIDATED `IssuedCertificate` exists AND its
            invalidation_reason is exactly
            `COMPLETION_REGRESSED_INVALIDATION_REASON` (the marker
            `calculate_course_progress` writes when recomputed progress
            fell below 100% — e.g. new content was added after completion)
            and the enrollment has legitimately re-completed
            (completion_date set + all assignments approved — the same
            gates as fresh issuance), the certificate is REVIVED:
            is_valid flipped back, invalidation fields cleared, enrollment
            re-stamped, and (existing_row, True) returned so callers treat
            it like a fresh issue. Without this, the first issuance would
            own the row forever and a re-completing student could never
            get their certificate back without a manual
            /certificates/regenerate. Any OTHER invalidation reason (an
            admin revoke, a manual invalidation) is TERMINAL: those certs
            are never auto-revived and return (existing_row, False).
          * Otherwise inserts a new `IssuedCertificate`, attempts PDF
            generation (best-effort — partial failure leaves a row with empty
            URL so the user can hit /certificates/regenerate), stamps
            Enrollment.certificate_id/certificate_url, and calls
            `grant_internship_eligibility_on_certificate` (the SPOC/internship
            hook).
          * Never raises. Rolls back on any DB error and returns (None, False).
            Certificates are best-effort from the caller's perspective — a
            broken cert must not break lesson-complete or quiz submit.

        Returns (certificate_row_or_none, newly_issued_bool).
        """
        from app.models.certificate import (
            IssuedCertificate,
            COMPLETION_REGRESSED_INVALIDATION_REASON,
        )
        from app.models.course import Course
        from app.models.user import User

        try:
            if enrollment is None:
                return None, False

            existing = db.query(IssuedCertificate).filter(
                IssuedCertificate.user_id == enrollment.user_id,
                IssuedCertificate.course_id == enrollment.course_id,
            ).first()

            if enrollment.completion_date is None:
                # Completion not (re-)established: nothing to issue, and an
                # invalidated certificate must stay invalidated until the
                # enrollment genuinely re-completes.
                return existing, False

            if existing:
                # Revive a regression-invalidated certificate on legitimate
                # re-completion. Same qualification gates as the fresh
                # issuance path below (completion_date is set above; every
                # assignment must have an approved GRADED submission).
                # GATED ON THE MARKER: only certificates invalidated by the
                # completion-regression branch of calculate_course_progress
                # (reason == COMPLETION_REGRESSED_INVALIDATION_REASON) may
                # come back. An admin revoke (any other reason) is a
                # deliberate, terminal decision and must survive every
                # subsequent recalc / issuance hook unchanged.
                if (
                    existing.is_valid is False
                    and existing.invalidation_reason
                    == COMPLETION_REGRESSED_INVALIDATION_REASON
                    and course_assignments_approved(
                        db, enrollment.user_id, enrollment.course_id
                    )
                ):
                    existing.is_valid = True
                    existing.invalidation_reason = ""
                    existing.invalidated_date = None
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
                        return existing, False

                    # Re-stamp enrollment (best-effort), mirroring the
                    # fresh-issuance path.
                    try:
                        enrollment.certificate_id = str(existing.id)
                        if existing.certificate_download_url:
                            enrollment.certificate_url = (
                                existing.certificate_download_url
                            )
                        db.commit()
                    except Exception:
                        db.rollback()

                    # Fire the SS2 internship hook, exactly like a fresh
                    # issue would (it is idempotent and swallows errors).
                    CertificateService.grant_internship_eligibility_on_certificate(
                        db, enrollment.user_id
                    )
                    return existing, True
                return existing, False

            course = db.query(Course).filter(Course.id == enrollment.course_id).first()
            if not course:
                return None, False

            # Gate: every assignment in the course must have an instructor/admin
            # -approved (GRADED) submission before the certificate can issue.
            # Courses with no assignments pass automatically.
            if not course_assignments_approved(db, enrollment.user_id, course.id):
                return None, False

            # Template chosen by the instructor for this course. `certificate_template`
            # stores the Certificate row id as a string; fall back to the default
            # template (id 1) when unset or pointing at a row that no longer exists,
            # so a bad value can never fail issuance (FK would otherwise reject it).
            from app.models.certificate import Certificate as _CertTemplate

            template_id = 1
            raw_tpl = (getattr(course, "certificate_template", "") or "").strip()
            if raw_tpl.isdigit():
                tid = int(raw_tpl)
                if db.query(_CertTemplate.id).filter(_CertTemplate.id == tid).first():
                    template_id = tid
            if not db.query(_CertTemplate.id).filter(_CertTemplate.id == template_id).first():
                # The default template row is missing (fresh database, seed
                # not run). The FK on IssuedCertificate.certificate_id would
                # reject the insert and issuance would silently fail for
                # EVERY course — the "Certificate not found" trap. Use any
                # existing template, and if the table is empty create a
                # default row so issuance can never deadlock on seed data.
                any_tpl = db.query(_CertTemplate.id).order_by(_CertTemplate.id).first()
                if any_tpl:
                    template_id = any_tpl[0]
                else:
                    fallback = _CertTemplate(
                        post_author=enrollment.user_id,
                        post_title="Certificate of Completion",
                        post_name="certificate-of-completion",
                        post_content="",
                    )
                    db.add(fallback)
                    db.flush()
                    template_id = fallback.id

            certificate_hash = CertificateService.generate_verification_code()
            secure_cert_id = CertificateService.generate_secure_certificate_id(
                user_id=enrollment.user_id,
                course_id=enrollment.course_id,
                issue_date=enrollment.completion_date,
            )

            # Populate the quiz/assignment completion columns (they default
            # to 0 and were previously never set) so certificates show the
            # real breakdown, not just the overall number. The overall
            # percentage falls back to 100 only when the tracker column is
            # NULL — a stored 0 must stay 0 (`or 100` used to mask it).
            quiz_pct, assignment_pct = course_completion_percentages(
                db, enrollment.user_id, enrollment.course_id
            )
            completion_pct = (
                enrollment.course_progress_percentage
                if enrollment.course_progress_percentage is not None
                else 100
            )

            new_cert = IssuedCertificate(
                certificate_id=template_id,  # instructor-chosen template, else default
                course_id=enrollment.course_id,
                user_id=enrollment.user_id,
                certificate_hash=certificate_hash,
                secure_certificate_id=secure_cert_id,
                certificate_title=f"Certificate of Completion - {course.post_title}",
                certificate_content="",
                completion_date=enrollment.completion_date,
                course_completion_percentage=completion_pct,
                quiz_completion_percentage=quiz_pct,
                assignment_completion_percentage=assignment_pct,
                certificate_download_url="",
            )
            db.add(new_cert)
            try:
                db.commit()
                db.refresh(new_cert)
            except IntegrityError:
                # Race: another worker inserted the (user_id, course_id) row
                # between our select-not-found and our insert. The new UNIQUE
                # constraint (uq_issued_certificate_user_course) fires here.
                # Roll back, re-read the winning row, return it as "existing".
                db.rollback()
                winner = db.query(IssuedCertificate).filter(
                    IssuedCertificate.user_id == enrollment.user_id,
                    IssuedCertificate.course_id == enrollment.course_id,
                ).first()
                return winner, False
            except Exception:
                db.rollback()
                return None, False

            # Best-effort PDF generation. If it fails, the row stays (empty
            # URL) and the user can regenerate via /certificates/regenerate.
            # We invoke the synchronous `_generate_pdf` helper directly to
            # avoid event-loop reentrancy from inside request handlers.
            try:
                from app.core.config import get_settings

                settings = get_settings()
                student = db.query(User).filter(User.id == enrollment.user_id).first()
                certificate_data = {
                    "student_name": student.display_name if student else "Student",
                    "course_title": course.post_title,
                    "instructor_name": course.instructor.display_name if course.instructor else "SashaInfinity",
                    "completion_date": enrollment.completion_date,
                    "course_duration": course.course_duration,
                    "certificate_id": str(new_cert.id),
                    "certificate_hash": certificate_hash,
                    "base_url": getattr(settings, "FRONTEND_URL", "https://lms.sashainfinity.com"),
                }
                cert_dir = "certificates"
                os.makedirs(cert_dir, exist_ok=True)
                filename = f"certificate_{uuid.uuid4().hex}.pdf"
                file_path = os.path.join(cert_dir, filename)
                CertificateService._generate_pdf(certificate_data, file_path)
                cert_url = f"/certificate-files/{filename}"

                new_cert.certificate_download_url = cert_url
                try:
                    db.commit()
                except Exception:
                    db.rollback()
            except Exception:
                # PDF failed — leave row intact with empty URL.
                try:
                    db.rollback()
                except Exception:
                    pass

            # Stamp enrollment (best-effort).
            try:
                enrollment.certificate_id = str(new_cert.id)
                if new_cert.certificate_download_url:
                    enrollment.certificate_url = new_cert.certificate_download_url
                db.commit()
            except Exception:
                db.rollback()

            # Fire SS2 internship hook (itself idempotent + swallows errors).
            CertificateService.grant_internship_eligibility_on_certificate(
                db, enrollment.user_id
            )

            # Warm the HTML render cache off-request. A cold certificate costs
            # ~8.5s of headless Chrome, and until now that cost landed on the
            # student the first time they opened their certificate. Doing it at
            # issue time means the page, the download and the social card all
            # hit a warm cache.
            CertificateService.warm_render_cache(new_cert)

            return new_cert, True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return None, False

    @staticmethod
    def warm_render_cache(certificate) -> None:
        """Pre-render the certificate PNG + WebP + PDF in a background thread.

        Best-effort and non-blocking: issuance must never fail or stall because
        a render did. The renderer's own semaphore still caps concurrent Chrome
        processes, so a batch of issuances queues rather than piling up.
        """
        secure_id = getattr(certificate, "secure_certificate_id", None)
        cert_hash = getattr(certificate, "certificate_hash", None)
        if not (secure_id and cert_hash):
            return

        # Detach from the request's Session — this outlives the response.
        snapshot = SimpleNamespace(
            secure_certificate_id=secure_id,
            certificate_hash=cert_hash,
        )

        def _warm():
            # WebP first: it renders the PNG on the way through, so the two
            # share one Chrome run instead of racing for the semaphore.
            for render in (
                CertificateService.get_or_render_html_webp,
                CertificateService.get_or_render_html_pdf,
            ):
                try:
                    render(snapshot)
                except Exception as exc:  # pragma: no cover - best effort
                    logger.warning(
                        "Certificate cache warm failed for %s: %s", secure_id, exc
                    )

        threading.Thread(
            target=_warm, name=f"cert-warm-{secure_id}", daemon=True
        ).start()

    @staticmethod
    async def generate_pdf_certificate(certificate) -> bytes:
        """Generate PDF bytes for download (legacy ReportLab design).

        Kept as the fallback for `generate_html_pdf_certificate`. Prefer
        `generate_html_pdf_certificate`, which renders the same design the
        user sees on screen (certificates/template.html).
        """
        return CertificateService._reportlab_pdf_bytes(certificate)

    @staticmethod
    def _reportlab_pdf_bytes(certificate) -> bytes:
        """Synchronous ReportLab PDF generation (the orange left-panel design)."""
        import tempfile
        data = {
            "student_name": certificate.user.display_name if hasattr(certificate, "user") else "Student",
            "course_title": certificate.course.post_title if hasattr(certificate, "course") else "Course",
            "instructor_name": "SashaInfinity",
            "completion_date": certificate.completion_date,
            "certificate_id": str(certificate.id),
            "certificate_hash": certificate.certificate_hash,
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        CertificateService._generate_pdf(data, path)
        with open(path, "rb") as f:
            content = f.read()
        os.remove(path)
        return content

    # Disk cache directory for rendered HTML certificate PDFs. Rendering with
    # headless Chrome is expensive (several seconds + CPU), so we render each
    # certificate once and serve the cached file on subsequent downloads.
    _html_pdf_cache_dir = "certificates"

    @staticmethod
    def _html_pdf_cache_path(certificate) -> str:
        safe_id = "".join(ch for ch in str(certificate.secure_certificate_id) if ch.isalnum())
        return os.path.join(CertificateService._html_pdf_cache_dir, f"cert_html_{safe_id}.pdf")

    @staticmethod
    def clear_html_pdf_cache(certificate) -> None:
        """Remove the cached HTML-rendered PDF (call on regenerate)."""
        try:
            path = CertificateService._html_pdf_cache_path(certificate)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    @staticmethod
    def get_or_render_html_pdf(certificate, internal_base_url: Optional[str] = None) -> bytes:
        """Return the HTML-template PDF for this certificate, rendering it with
        headless Chrome only on a cache miss.

        On a successful Chrome render the result is cached to disk so repeated
        downloads are instant and don't re-spawn Chrome. If Chrome rendering
        fails, falls back to the legacy ReportLab design *without* caching it
        (so a later download will retry the proper render).
        """
        cache_path = CertificateService._html_pdf_cache_path(certificate)
        try:
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1024:
                with open(cache_path, "rb") as f:
                    return f.read()
        except OSError:
            pass

        try:
            pdf = CertificateService._render_pdf_dispatch(certificate, internal_base_url)
        except Exception:
            # Chrome unavailable / render failed — serve the fallback design but
            # do NOT cache it, so the next request retries the real render.
            #
            # This used to swallow the error silently, so a broken Chrome
            # simply produced a different-looking certificate with nothing in
            # the logs to explain it. Downloads "work" but emit the wrong
            # design — log loudly so the real cause is visible.
            logger.exception(
                "Chrome render failed for certificate %s — serving ReportLab fallback design",
                getattr(certificate, "secure_certificate_id", getattr(certificate, "id", "?")),
            )
            return CertificateService._reportlab_pdf_bytes(certificate)

        try:
            os.makedirs(CertificateService._html_pdf_cache_dir, exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(pdf)
        except OSError:
            pass
        return pdf

    @staticmethod
    def generate_html_pdf_certificate(certificate, internal_base_url: Optional[str] = None) -> bytes:
        """Render the certificate PDF from the HTML template, best-effort.

        Thin wrapper: try headless Chrome, fall back to the legacy ReportLab
        design if rendering fails so a download never 500s. Prefer
        `get_or_render_html_pdf`, which additionally caches the result.
        """
        try:
            return CertificateService._render_pdf_dispatch(certificate, internal_base_url)
        except Exception:
            logger.exception(
                "Chrome render failed for certificate %s — serving ReportLab fallback design",
                getattr(certificate, "secure_certificate_id", getattr(certificate, "id", "?")),
            )
            return CertificateService._reportlab_pdf_bytes(certificate)

    # ------------------------------------------------------------------
    # PNG image of the certificate — used for the FAST on-screen view so the
    # preview doesn't have to download + JS-unpack the 1.1MB bundle.
    # ------------------------------------------------------------------
    @staticmethod
    def _png_cache_path(certificate) -> str:
        safe_id = "".join(ch for ch in str(certificate.secure_certificate_id) if ch.isalnum())
        return os.path.join(CertificateService._html_pdf_cache_dir, f"cert_img_{safe_id}.png")

    @staticmethod
    def clear_png_cache(certificate) -> None:
        try:
            path = CertificateService._png_cache_path(certificate)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    @staticmethod
    def get_or_render_html_png(certificate, internal_base_url: Optional[str] = None) -> Optional[bytes]:
        """Return a cached PNG of the certificate, rendering it via headless
        Chrome on a cache miss. Returns None if rendering fails (caller can
        decide how to handle — e.g. the fast view falls back to the bundle)."""
        cache_path = CertificateService._png_cache_path(certificate)
        try:
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1024:
                with open(cache_path, "rb") as f:
                    return f.read()
        except OSError:
            pass

        try:
            png = CertificateService._render_png_dispatch(certificate, internal_base_url)
        except Exception:
            return None

        try:
            os.makedirs(CertificateService._html_pdf_cache_dir, exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(png)
        except OSError:
            pass
        return png

    # ------------------------------------------------------------------
    # WebP of the same render.
    #
    # The Chrome screenshot is a 1800x1158 PNG — 1.36MB on production. PNG
    # stores a photographic certificate badly, and the preview shipped every
    # one of those bytes on every view. The identical image as WebP is ~100KB.
    # The PNG is kept as the source of truth (and for clients that don't ask
    # for WebP — notably LinkedIn's crawler, which renders og:image itself).
    # ------------------------------------------------------------------
    _WEBP_QUALITY = 82

    @staticmethod
    def _webp_cache_path(certificate) -> str:
        safe_id = "".join(ch for ch in str(certificate.secure_certificate_id) if ch.isalnum())
        return os.path.join(CertificateService._html_pdf_cache_dir, f"cert_img_{safe_id}.webp")

    @staticmethod
    def clear_webp_cache(certificate) -> None:
        try:
            path = CertificateService._webp_cache_path(certificate)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    @staticmethod
    def png_to_webp(png: bytes) -> Optional[bytes]:
        """Re-encode PNG bytes as WebP. Returns None if the input won't decode,
        so callers degrade to serving the PNG rather than failing the request."""
        try:
            from io import BytesIO

            from PIL import Image

            with Image.open(BytesIO(png)) as im:
                out = BytesIO()
                im.convert("RGB").save(
                    out, "WEBP", quality=CertificateService._WEBP_QUALITY, method=6
                )
                return out.getvalue()
        except Exception:
            return None

    @staticmethod
    def get_or_render_html_webp(certificate, internal_base_url: Optional[str] = None) -> Optional[bytes]:
        """Return a cached WebP of the certificate, converting from the cached
        PNG on a miss (rendering it first if that is missing too).

        Returns None if there is no PNG to convert or the conversion fails —
        the caller then serves the PNG.
        """
        cache_path = CertificateService._webp_cache_path(certificate)
        try:
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 512:
                with open(cache_path, "rb") as f:
                    return f.read()
        except OSError:
            pass

        png = CertificateService.get_or_render_html_png(certificate, internal_base_url)
        if not png:
            return None

        webp = CertificateService.png_to_webp(png)
        if not webp:
            return None

        try:
            os.makedirs(CertificateService._html_pdf_cache_dir, exist_ok=True)
            with open(cache_path, "wb") as f:
                f.write(webp)
        except OSError:
            pass
        return webp

    @staticmethod
    def _load_html_for_dispatch(certificate) -> Optional[Tuple[str, int, int]]:
        """If this certificate's template uses the elements_config render
        path, return (html, width_px, height_px); otherwise None so the
        caller falls back to the legacy verify-URL Chrome render.

        Opens its OWN short-lived DB session — `certificate` passed in here
        may be a detached SimpleNamespace snapshot (warm_render_cache runs in
        a background thread with no request-scoped session available), so
        this cannot rely on `certificate`'s own session/relationships. Only
        `secure_certificate_id` + `certificate_hash` are guaranteed present.
        """
        secure_id = getattr(certificate, "secure_certificate_id", None)
        cert_hash = getattr(certificate, "certificate_hash", None)
        if not (secure_id and cert_hash):
            return None

        from app.core.database import SessionLocal
        from app.models.certificate import IssuedCertificate

        db = SessionLocal()
        try:
            row = db.query(IssuedCertificate).filter(
                IssuedCertificate.secure_certificate_id == secure_id,
                IssuedCertificate.certificate_hash == cert_hash,
            ).first()
            if row is None:
                return None
            template = CertificateService.resolve_certificate_template_row(db, row)
            if not CertificateService.template_uses_elements_config(template):
                return None
            html_content = CertificateService.build_certificate_html_for_issued(db, row)
            if not html_content:
                return None
            width = int(getattr(template, "certificate_width", 1400) or 1400)
            height = int(getattr(template, "certificate_height", 1080) or 1080)
            return html_content, width, height
        except Exception:
            logger.warning("certificate_service: elements_config dispatch lookup failed", exc_info=True)
            return None
        finally:
            db.close()

    @staticmethod
    def _render_pdf_dispatch(certificate, internal_base_url: Optional[str] = None) -> bytes:
        """Render this certificate to PDF, preferring the elements_config
        HTML path when the template uses it; falls back to the legacy
        verify-URL Chrome render for post_name-slug (file-based) templates.
        Raises on failure (caller decides whether to fall back further, to
        ReportLab)."""
        dispatch = CertificateService._load_html_for_dispatch(certificate)
        if dispatch is not None:
            html_content, width, height = dispatch
            return CertificateService._render_local_html_pdf_via_chrome(html_content, width, height)
        return CertificateService._render_html_pdf_via_chrome(certificate, internal_base_url)

    @staticmethod
    def _render_png_dispatch(certificate, internal_base_url: Optional[str] = None) -> bytes:
        """PNG counterpart of `_render_pdf_dispatch`."""
        dispatch = CertificateService._load_html_for_dispatch(certificate)
        if dispatch is not None:
            html_content, width, height = dispatch
            return CertificateService._render_local_html_png_via_chrome(html_content, width, height)
        return CertificateService._render_html_png_via_chrome(certificate, internal_base_url)

    @staticmethod
    def _render_html_png_via_chrome(certificate, internal_base_url: Optional[str] = None) -> bytes:
        """Screenshot just the certificate card (#cert) from the full bundle
        page at 2x scale, for a crisp image. Raises on failure."""
        import time

        from app.core.config import get_settings

        settings = get_settings()
        base = (
            internal_base_url
            or getattr(settings, "INTERNAL_BASE_URL", None)
            or "http://127.0.0.1:8000"
        )
        verify_url = (
            f"{base}/api/v1/certificates/verify-certificate"
            f"?id={certificate.secure_certificate_id}&hash={certificate.certificate_hash}&full=1"
        )

        driver = None
        # Bounded wait for a render slot. A timed-out acquire used to fall
        # straight through and launch Chrome regardless, so a burst of
        # downloads ignored the cap of 2 entirely and could exhaust the
        # container's memory — taking the renders down with it. Give up
        # instead and let the caller fall back to the ReportLab renderer.
        if not CertificateService._render_semaphore.acquire(timeout=60):
            raise RuntimeError(
                "Timed out waiting for a certificate render slot (renderer saturated)"
            )
        acquired = True
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--hide-scrollbars")
            opts.add_argument("--window-size=1400,1000")
            # 1.5x keeps text crisp on screen while keeping the PNG light
            # (~1.2MB) for a fast first paint.
            opts.add_argument("--force-device-scale-factor=1.5")
            opts.add_argument("--no-zygote")
            opts.add_argument("--disable-crash-reporter")
            opts.add_argument("--disable-breakpad")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-software-rasterizer")

            driver = CertificateService._build_chrome_driver(opts)
            driver.set_page_load_timeout(40)
            driver.get(verify_url)
            try:
                WebDriverWait(driver, 25).until(
                    lambda d: d.execute_script(
                        "return !document.getElementById('__bundler_loading')"
                    )
                )
            except Exception:
                pass
            time.sleep(1.5)

            # Capture just the certificate card for a clean, cropped image.
            try:
                el = driver.find_element(By.ID, "cert")
                return el.screenshot_as_png
            except Exception:
                return driver.get_screenshot_as_png()
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if acquired:
                CertificateService._render_semaphore.release()

    @staticmethod
    def _write_temp_html(html_content: str) -> str:
        """Write an HTML document to a scratch temp file and return its path.
        Caller is responsible for cleanup.

        Deliberately OUTSIDE `certificates/` (`_html_pdf_cache_dir`), which is
        mounted publicly at /certificate-files — a rendered certificate's HTML
        contains the same student/course data the public verify page already
        shows, but there is no reason to let it sit in a statically-served
        directory even briefly. Mirrors the H5P temp-upload dir fix (moved
        outside the /uploads static mount for the same reason).
        """
        import uuid as _uuid

        cert_dir = CertificateService._html_pdf_cache_dir
        tmp_dir = CertificateService._render_tmp_dir()
        os.makedirs(tmp_dir, exist_ok=True)
        path = os.path.join(tmp_dir, f"cert_render_{_uuid.uuid4().hex}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return path

    @staticmethod
    def _render_tmp_dir() -> str:
        cert_dir = CertificateService._html_pdf_cache_dir
        return os.path.join(os.path.dirname(os.path.abspath(cert_dir)) or ".", "certificates_render_tmp")

    @staticmethod
    def purge_stale_render_tmp(max_age_seconds: int = 3600) -> int:
        """L-3: best-effort startup purge of certificates_render_tmp/ files
        older than `max_age_seconds` (default 1h).

        Every file in this directory is deleted in its own `finally` block
        immediately after a render (_render_local_html_pdf_via_chrome /
        _render_local_html_png_via_chrome), so under normal operation it's
        empty — this purge only matters after a crash/kill mid-render that
        skipped the cleanup. Cheap glob+unlink; never raises.
        """
        import glob
        import time as _time

        removed = 0
        try:
            tmp_dir = CertificateService._render_tmp_dir()
            if not os.path.isdir(tmp_dir):
                return 0
            cutoff = _time.time() - max_age_seconds
            for path in glob.glob(os.path.join(tmp_dir, "cert_render_*.html")):
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path)
                        removed += 1
                except OSError:
                    continue
        except Exception:
            logger.warning("certificate_service: stale render-tmp purge failed", exc_info=True)
        return removed

    @staticmethod
    def _render_local_html_pdf_via_chrome(html_content: str, page_width_px: int, page_height_px: int) -> bytes:
        """Render an arbitrary self-contained HTML string to PDF via headless
        Chrome, navigating to a local `file://` temp file rather than a
        server URL — the variant elements_config rendering needs, since that
        HTML is generated on the fly and never has to be a routable page.

        Shares the same render semaphore + Chrome driver construction as
        `_render_html_pdf_via_chrome` so a burst of dynamic-template renders
        is capped exactly like the legacy path. Raises on any failure (the
        caller decides whether to fall back to ReportLab).
        """
        import base64
        import time

        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.print_page_options import PrintOptions
        from selenium.webdriver.support.ui import WebDriverWait

        temp_path = CertificateService._write_temp_html(html_content)
        driver = None
        if not CertificateService._render_semaphore.acquire(timeout=60):
            raise RuntimeError(
                "Timed out waiting for a certificate render slot (renderer saturated)"
            )
        acquired = True
        try:
            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--hide-scrollbars")
            opts.add_argument(f"--window-size={max(page_width_px, 200)},{max(page_height_px, 200)}")
            opts.add_argument("--no-zygote")
            opts.add_argument("--disable-crash-reporter")
            opts.add_argument("--disable-breakpad")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-software-rasterizer")

            driver = CertificateService._build_chrome_driver(opts)
            driver.set_page_load_timeout(40)
            # file:// URL — Selenium's .get() accepts a bare filesystem path
            # too, but the explicit scheme is more portable across drivers.
            file_url = "file:///" + os.path.abspath(temp_path).replace(os.sep, "/")
            driver.get(file_url)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass
            # Give web fonts + the QR <img> a beat to paint before printing.
            time.sleep(1.0)

            print_opts = PrintOptions()
            print_opts.background = True
            print_opts.margin_top = 0
            print_opts.margin_bottom = 0
            print_opts.margin_left = 0
            print_opts.margin_right = 0
            # Page size derived from the certificate's own pixel dimensions
            # (converted to inches at 96 DPI, then to cm) so the PDF page is
            # sized exactly to the design — no cropping, no white bands,
            # regardless of orientation/aspect ratio.
            cm_per_px = 2.54 / 96.0
            print_opts.page_width = max(page_width_px * cm_per_px, 5.0)
            print_opts.page_height = max(page_height_px * cm_per_px, 5.0)
            print_opts.scale = 1.0
            print_opts.shrink_to_fit = True

            b64 = driver.print_page(print_opts)
            return base64.b64decode(b64)
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if acquired:
                CertificateService._render_semaphore.release()
            try:
                os.remove(temp_path)
            except OSError:
                pass

    @staticmethod
    def _render_local_html_png_via_chrome(html_content: str, page_width_px: int, page_height_px: int) -> bytes:
        """Screenshot an arbitrary self-contained HTML string via headless
        Chrome, navigating to a local `file://` temp file. Raises on failure."""
        import time

        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait

        temp_path = CertificateService._write_temp_html(html_content)
        driver = None
        if not CertificateService._render_semaphore.acquire(timeout=60):
            raise RuntimeError(
                "Timed out waiting for a certificate render slot (renderer saturated)"
            )
        acquired = True
        try:
            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--hide-scrollbars")
            opts.add_argument(f"--window-size={max(page_width_px, 200)},{max(page_height_px, 200)}")
            opts.add_argument("--force-device-scale-factor=1.5")
            opts.add_argument("--no-zygote")
            opts.add_argument("--disable-crash-reporter")
            opts.add_argument("--disable-breakpad")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-software-rasterizer")

            driver = CertificateService._build_chrome_driver(opts)
            driver.set_page_load_timeout(40)
            file_url = "file:///" + os.path.abspath(temp_path).replace(os.sep, "/")
            driver.get(file_url)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass
            time.sleep(1.0)

            from selenium.webdriver.common.by import By

            try:
                el = driver.find_element(By.ID, "cert-page")
                return el.screenshot_as_png
            except Exception:
                return driver.get_screenshot_as_png()
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if acquired:
                CertificateService._render_semaphore.release()
            try:
                os.remove(temp_path)
            except OSError:
                pass

    @staticmethod
    def _render_html_pdf_via_chrome(certificate, internal_base_url: Optional[str] = None) -> bytes:
        """Render the certificate to PDF from the HTML template (the
        `certificates/template.html` "Certificate of Excellence" design) using
        headless Chrome, so the downloaded PDF matches the on-screen preview /
        verify page exactly.

        We navigate headless Chrome to the public verify-certificate URL (the
        same page the frontend embeds in its preview iframe), let the
        self-unpacking template bundle finish, then print the page to PDF in
        landscape. The verify page already injects the print stylesheet that
        hides buttons and lays the certificate out full-bleed.

        Raises on any failure (caller decides whether to fall back).
        """
        import base64
        import time

        from app.core.config import get_settings

        settings = get_settings()
        base = (
            internal_base_url
            or getattr(settings, "INTERNAL_BASE_URL", None)
            or "http://127.0.0.1:8000"
        )
        verify_url = (
            f"{base}/api/v1/certificates/verify-certificate"
            f"?id={certificate.secure_certificate_id}&hash={certificate.certificate_hash}&full=1"
        )

        driver = None
        # Bounded wait for a render slot. A timed-out acquire used to fall
        # straight through and launch Chrome regardless, so a burst of
        # downloads ignored the cap of 2 entirely and could exhaust the
        # container's memory — taking the renders down with it. Give up
        # instead and let the caller fall back to the ReportLab renderer.
        if not CertificateService._render_semaphore.acquire(timeout=60):
            raise RuntimeError(
                "Timed out waiting for a certificate render slot (renderer saturated)"
            )
        acquired = True
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.print_page_options import PrintOptions
            from selenium.webdriver.support.ui import WebDriverWait

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--hide-scrollbars")
            opts.add_argument("--window-size=1600,1200")
            # Reduce the number of helper subprocesses Chrome spawns (zygote,
            # crash reporter, extensions) so fewer can be left as zombies.
            opts.add_argument("--no-zygote")
            opts.add_argument("--disable-crash-reporter")
            opts.add_argument("--disable-breakpad")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-software-rasterizer")

            driver = CertificateService._build_chrome_driver(opts)
            driver.set_page_load_timeout(40)
            driver.get(verify_url)

            # The template is a self-unpacking bundle that removes the
            # #__bundler_loading node once it has rendered. Wait for that,
            # then a short beat for the QR canvas to paint.
            try:
                WebDriverWait(driver, 25).until(
                    lambda d: d.execute_script(
                        "return !document.getElementById('__bundler_loading')"
                    )
                )
            except Exception:
                pass
            time.sleep(1.5)

            print_opts = PrintOptions()
            print_opts.orientation = "landscape"
            print_opts.background = True
            print_opts.margin_top = 0
            print_opts.margin_bottom = 0
            print_opts.margin_left = 0
            print_opts.margin_right = 0
            # A4 paper (cm). With landscape orientation this yields a
            # 29.7 x 21.0 cm page (ratio 1.414), matching the certificate's
            # native 1200x850 (ratio 1.412) — so the cert fills the page with
            # no white bands or cropping. Default Letter (1.294) did not match.
            print_opts.page_width = 21.0
            print_opts.page_height = 29.7
            print_opts.scale = 1.0
            print_opts.shrink_to_fit = True

            b64 = driver.print_page(print_opts)
            return base64.b64decode(b64)
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            if acquired:
                CertificateService._render_semaphore.release()
