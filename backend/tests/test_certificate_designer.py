"""Certificate engine unification: elements_config renderer, QR, instructor
designer API (Task 6 of the Learning Experience plan).

Covers docs/superpowers/specs/2026-09-02-learning-experience-design.md
section C items 1, 2, 3, 6:

  - app/services/certificate_html_renderer.py: HTML generation from
    elements_config — typed tokens substituted + HTML-escaped (including a
    <script> injection attempt in a student name), QR data-URI present,
    curated fonts linked via Google Fonts, rotation/z-index rendered, page
    sized from certificate_width/height.
  - Instructor designer API /api/v1/certificates/designer: scoping matrix
    (own / foreign instructor / global / admin), delete blocked when
    referenced by a course or an issued certificate, elements_config
    validation matrix (unknown type, out-of-bounds numeric, over the
    100-element cap, non-curated font silently falls back).
  - Legacy slug (post_name) issued-certificate path is untouched —
    resolve_template_path still resolves a slug row to its file, and
    CertificateService.template_uses_elements_config() is False for it even
    when elements_config happens to be non-empty.
  - Preview endpoint returns a data: URI. Chrome is very likely absent on
    this box (no pinned chromedriver, no browser installed) — the endpoint's
    ReportLab fallback (plan-noted: "the ReportLab fallback must make the
    test deterministic; detect and note") is what actually makes this
    assertion pass in CI, and the test explicitly accepts either renderer so
    it stays green identically in an environment that DOES have Chrome.

Fix round (coordinator review — 2 HIGH + 2 MEDIUM + 3 LOW, PoC-proven):
  - H-1: image_url/signature src/background_image src allowlist (same-origin
    /uploads|/certificate-files paths or data:image/... URIs only) — REJECTED
    at write time (designer API 422), DROPPED at render time (defense in
    depth for rows predating validation). file://, blob:, external http(s)
    all rejected/dropped.
  - H-2: CSS-context injection via color/border/font_weight/text_align/
    letter_spacing neutralized by strict allowlist validators — the emitted
    style carries only a normalized value, never the raw attacker string.
  - M-1: /certificates/templates/list (anonymous/public) no longer leaks
    private instructor drafts — scoped to legacy-slug OR is_global rows.
  - M-2: designer PUT invalidates every IssuedCertificate's rendered cache
    for that template so a corrected design doesn't keep serving stale PDFs.
"""
from datetime import datetime, timezone

import pytest

from app.models.certificate import Certificate, IssuedCertificate
from app.models.course import Course
from app.services.certificate_html_renderer import (
    CURATED_FONTS,
    build_certificate_html,
    is_safe_asset_src,
    sample_values,
    validate_border,
    validate_color,
    validate_font_weight,
    validate_letter_spacing,
)
from app.services.certificate_service import CertificateService


# ----- factories (mirrors test_gradebook.py / test_assessment_integrity.py) --


def _approve_instructor(db, user):
    from app.models.user import InstructorProfile

    profile = db.query(InstructorProfile).filter_by(user_id=user.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=user.id, is_approved=True))
    db.commit()
    return user


def _make_approved_instructor(db, make_user, email):
    instructor = make_user(role="instructor", email=email)
    return _approve_instructor(db, instructor)


def _admin_headers(client, db, admin):
    """Admin logins require TOTP 2FA — enrol a secret and send the current
    code (mirrors test_gradebook._admin_headers)."""
    import pyotp
    from app.core import totp

    admin.totp_enabled = True
    admin.totp_secret = totp.generate_secret()
    db.commit()
    r = client.post(
        "/api/v1/auth/login",
        json={
            "email": admin.user_email,
            "password": admin._test_password,
            "otp_code": pyotp.TOTP(admin.totp_secret).now(),
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_course(db, instructor, title="Designer Course"):
    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="content",
        post_excerpt="excerpt",
        post_status="published",
        post_name=title.lower().replace(" ", "-"),
        course_thumbnail="",
        course_price=0,
        course_level="beginner",
        course_category="Meiporul",
        course_language="English",
        course_duration="10",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def _simple_elements(n=1):
    return [
        {
            "type": "student_name", "x": 10, "y": 10, "width": 300, "height": 40,
            "font_family": "Inter", "font_size": 24, "z_index": i,
        }
        for i in range(n)
    ]


def _designer_template(db, author, *, elements=None, is_global=False, post_name=""):
    tpl = Certificate(
        post_author=author.id,
        post_title="Test Template",
        post_content="",
        post_status="publish",
        post_type="tutor_certificates",
        post_name=post_name,
        certificate_orientation="landscape",
        certificate_width=1400,
        certificate_height=1000,
        background_color="#ffffff",
        background_image="",
        elements_config=elements if elements is not None else _simple_elements(),
        is_global=is_global,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


# =============================================================================
# 1. HTML generation (build_certificate_html)
# =============================================================================


class TestHtmlGeneration:
    def test_tokens_substituted_and_escaped(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "student_name", "x": 0, "y": 0, "width": 300, "height": 40},
                {"type": "course_name", "x": 0, "y": 50, "width": 300, "height": 40},
                {"type": "completion_date", "x": 0, "y": 100, "width": 300, "height": 40},
                {"type": "certificate_id", "x": 0, "y": 150, "width": 300, "height": 40},
                {"type": "instructor_name", "x": 0, "y": 200, "width": 300, "height": 40},
            ],
        )
        values = sample_values("SEC-1")
        html = build_certificate_html(tpl, values)
        for key in ("student_name", "course_name", "completion_date", "certificate_id", "instructor_name"):
            assert values[key] in html, f"{key} value not substituted"

    def test_script_injection_in_student_name_is_escaped(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[{"type": "student_name", "x": 0, "y": 0, "width": 300, "height": 40}],
        )
        values = sample_values("SEC-2")
        values["student_name"] = "<script>alert('xss')</script>"
        html = build_certificate_html(tpl, values)
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_course_name_injection_via_attribute_breakout_is_escaped(self):
        """A course title trying to break out of an attribute context (not
        just a text node) must still come out neutralized."""
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[{"type": "course_name", "x": 0, "y": 0, "width": 300, "height": 40}],
        )
        values = sample_values("SEC-3")
        values["course_name"] = '"><img src=x onerror=alert(1)>'
        html = build_certificate_html(tpl, values)
        assert "<img src=x onerror" not in html
        assert "&quot;&gt;&lt;img" in html

    def test_qr_code_data_uri_present(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[{"type": "qr_code", "x": 10, "y": 10, "width": 120, "height": 120}],
        )
        values = sample_values("SEC-4")
        html = build_certificate_html(tpl, values)
        assert "data:image/png;base64," in html
        assert "cert-el-qr" in html

    def test_qr_code_absent_without_verify_url(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[{"type": "qr_code", "x": 10, "y": 10, "width": 120, "height": 120}],
        )
        values = {"student_name": "X", "course_name": "Y", "completion_date": "Z",
                  "certificate_id": "1", "instructor_name": "I", "verify_url": ""}
        html = build_certificate_html(tpl, values)
        assert "data:image/png;base64," not in html

    def test_curated_fonts_linked_via_google_fonts(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "student_name", "x": 0, "y": 0, "width": 300, "height": 40,
                 "font_family": "Playfair Display"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-5"))
        assert "fonts.googleapis.com" in html
        assert "Playfair+Display" in html
        assert "'Playfair Display'" in html

    def test_non_curated_font_falls_back_without_arbitrary_google_fonts_request(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "student_name", "x": 0, "y": 0, "width": 300, "height": 40,
                 "font_family": "Comic Sans MS"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-6"))
        # Never request a Google Fonts family that isn't in the curated list.
        assert "Comic+Sans" not in html
        assert "'Inter'" in html  # fallback family

    def test_rotation_and_z_index_rendered(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "Back", "x": 0, "y": 0, "width": 100, "height": 40,
                 "rotation": 15, "z_index": 1},
                {"type": "text", "content": "Front", "x": 0, "y": 0, "width": 100, "height": 40,
                 "rotation": -7, "z_index": 5},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-7"))
        assert "rotate(15.0deg)" in html
        assert "rotate(-7.0deg)" in html
        assert "z-index:1" in html
        assert "z-index:5" in html
        # Paint order follows z_index — "Back" (z=1) must appear before
        # "Front" (z=5) in the document.
        assert html.index(">Back<") < html.index(">Front<")

    def test_page_size_matches_certificate_dimensions(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1600, certificate_height=1100,
            background_color="#ffffff", background_image="", elements_config=[],
        )
        html = build_certificate_html(tpl, sample_values("SEC-8"))
        assert "width: 1600px" in html
        assert "height: 1100px" in html
        assert "size: 1600px 1100px" in html  # @page rule

    def test_unknown_element_type_silently_skipped(self):
        """A stray/unknown type must not crash rendering (defense in depth —
        the designer API validates on write, but the renderer itself stays
        forgiving so a stored row from before validation existed still
        renders instead of 500ing)."""
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[{"type": "mystery_widget", "x": 0, "y": 0, "width": 10, "height": 10}],
        )
        html = build_certificate_html(tpl, sample_values("SEC-9"))
        assert "cert-page" in html  # rendered without raising

    def test_rect_and_line_and_signature_render(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "rect", "x": 0, "y": 0, "width": 200, "height": 100,
                 "background_color": "#eeeeee", "border_radius": 8},
                {"type": "line", "x": 0, "y": 0, "width": 200, "height": 2, "line_thickness": 3},
                {"type": "signature_image", "x": 0, "y": 0, "width": 150, "height": 60,
                 "image_url": "/uploads/certificates/sig.png"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-10"))
        assert "cert-el-rect" in html
        assert "cert-el-line" in html
        assert "cert-el-signature" in html
        assert "border-radius:8.0px" in html
        assert "border-top:3.0px solid" in html


# =============================================================================
# 2. Legacy slug path untouched (regression guard)
# =============================================================================


class TestLegacySlugPathUntouched:
    def test_slug_row_never_uses_elements_config_path_even_if_populated(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "legacy1@example.com")
        # A slug row that ALSO happens to carry elements_config (e.g. stale
        # data) must still resolve to the legacy file path — the slug wins.
        tpl = _designer_template(
            db, instructor, elements=_simple_elements(), post_name="ivory-classic"
        )
        assert CertificateService.template_uses_elements_config(tpl) is False

    def test_row_with_no_slug_and_elements_config_uses_dynamic_path(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "legacy2@example.com")
        tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="")
        assert CertificateService.template_uses_elements_config(tpl) is True

    def test_row_with_empty_elements_config_does_not_use_dynamic_path(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "legacy3@example.com")
        tpl = _designer_template(db, instructor, elements=[], post_name="")
        assert CertificateService.template_uses_elements_config(tpl) is False

    def test_resolve_template_path_still_resolves_slug_to_file(self, db, make_user, tmp_path, monkeypatch):
        """routers/certificates.resolve_template_path is untouched by this
        task — a slug row must still resolve to its templates/<slug>.html
        file path shape regardless of elements_config.

        _CERT_ROOT is hardcoded to /app/certificates (the Docker container
        path), which doesn't exist on this dev box — resolve_template_path's
        documented fallback-to-default behavior kicks in for ANY slug here,
        which would be true with or without Task 6's changes. Point
        _TEMPLATES_DIR at a real temp dir with the file present so this test
        actually exercises the slug-resolution branch instead of always
        hitting the "file missing" fallback.
        """
        import app.routers.certificates as certs_router

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "ivory-classic.html").write_text("<html>Ivory Classic</html>", encoding="utf-8")
        monkeypatch.setattr(certs_router, "_TEMPLATES_DIR", templates_dir)

        instructor = _make_approved_instructor(db, make_user, "legacy4@example.com")
        tpl = _designer_template(db, instructor, elements=[], post_name="ivory-classic")

        issued = IssuedCertificate(
            certificate_id=tpl.id, course_id=1, user_id=instructor.id,
            certificate_hash="h" * 20, secure_certificate_id="S" * 20,
            certificate_title="t", completion_date=datetime.now(timezone.utc),
        )
        db.add(issued)
        db.commit()
        db.refresh(issued)

        path = certs_router.resolve_template_path(db, issued)
        assert path.name == "ivory-classic.html"

    def test_build_certificate_html_for_issued_returns_none_for_slug_row(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "legacy5@example.com")
        tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="midnight-gold")
        issued = IssuedCertificate(
            certificate_id=tpl.id, course_id=1, user_id=instructor.id,
            certificate_hash="h" * 20, secure_certificate_id="S" * 20,
            certificate_title="t", completion_date=datetime.now(timezone.utc),
        )
        db.add(issued)
        db.commit()
        db.refresh(issued)

        result = CertificateService.build_certificate_html_for_issued(db, issued)
        assert result is None

    def test_build_certificate_html_for_issued_returns_html_for_dynamic_row(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "legacy6@example.com")
        tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="")
        issued = IssuedCertificate(
            certificate_id=tpl.id, course_id=1, user_id=instructor.id,
            certificate_hash="h" * 20, secure_certificate_id="S" * 20,
            certificate_title="t", completion_date=datetime.now(timezone.utc),
        )
        db.add(issued)
        db.commit()
        db.refresh(issued)

        result = CertificateService.build_certificate_html_for_issued(db, issued)
        assert result is not None
        assert "cert-page" in result


# =============================================================================
# 3. Designer API scoping matrix
# =============================================================================


class TestDesignerScoping:
    def test_instructor_sees_own_but_not_foreign_non_global(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "owner@example.com")
        other = _make_approved_instructor(db, make_user, "other@example.com")
        _designer_template(db, owner)

        headers = auth_headers(other.user_email, other._test_password)
        r = client.get("/api/v1/certificates/designer/", headers=headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_instructor_sees_own_template(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "owner2@example.com")
        tpl = _designer_template(db, owner)

        headers = auth_headers(owner.user_email, owner._test_password)
        r = client.get("/api/v1/certificates/designer/", headers=headers)
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()]
        assert tpl.id in ids
        assert r.json()[[t["id"] for t in r.json()].index(tpl.id)]["is_own"] is True

    def test_instructor_sees_global_template_readonly(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "gowner@example.com")
        viewer = _make_approved_instructor(db, make_user, "gviewer@example.com")
        tpl = _designer_template(db, owner, is_global=True)

        headers = auth_headers(viewer.user_email, viewer._test_password)
        r = client.get("/api/v1/certificates/designer/", headers=headers)
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()]
        assert tpl.id in ids
        row = next(t for t in r.json() if t["id"] == tpl.id)
        assert row["is_own"] is False
        assert row["is_global"] is True

        # Read-only: viewer cannot edit it.
        r2 = client.put(
            f"/api/v1/certificates/designer/{tpl.id}",
            json={"name": "Hacked"},
            headers=headers,
        )
        assert r2.status_code == 403

    def test_admin_sees_all_templates(self, client, db, make_user, auth_headers):
        from app.core.security import get_password_hash
        from app.models.user import User

        owner = _make_approved_instructor(db, make_user, "aowner@example.com")
        _designer_template(db, owner)

        admin = User(
            user_login="cd_admin", user_pass=get_password_hash("Test@123"),
            user_nicename="cd_admin", user_email="cdadmin@example.com",
            display_name="CD Admin", role="admin", is_active=True, is_verified=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin._test_password = "Test@123"

        headers = _admin_headers(client, db, admin)
        r = client.get("/api/v1/certificates/designer/", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_admin_can_edit_any_template(self, client, db, make_user, auth_headers):
        from app.core.security import get_password_hash
        from app.models.user import User

        owner = _make_approved_instructor(db, make_user, "aowner2@example.com")
        tpl = _designer_template(db, owner)

        admin = User(
            user_login="cd_admin2", user_pass=get_password_hash("Test@123"),
            user_nicename="cd_admin2", user_email="cdadmin2@example.com",
            display_name="CD Admin 2", role="admin", is_active=True, is_verified=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin._test_password = "Test@123"

        headers = _admin_headers(client, db, admin)
        r = client.put(
            f"/api/v1/certificates/designer/{tpl.id}",
            json={"name": "Admin Edited"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Admin Edited"

    def test_only_admin_can_toggle_is_global(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "gtoggle@example.com")
        tpl = _designer_template(db, owner)

        headers = auth_headers(owner.user_email, owner._test_password)
        r = client.put(
            f"/api/v1/certificates/designer/{tpl.id}",
            json={"is_global": True},
            headers=headers,
        )
        assert r.status_code == 403

    def test_student_forbidden(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="student1@example.com")
        headers = auth_headers(student.user_email, student._test_password)
        r = client.get("/api/v1/certificates/designer/", headers=headers)
        assert r.status_code == 403

    def test_create_scopes_to_current_user(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "creator@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "My New Template",
                "elements_config": _simple_elements(),
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["post_author"] == instructor.id
        assert body["is_own"] is True
        assert body["is_global"] is False

    def test_duplicate_creates_own_copy_of_global_template(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "downer@example.com")
        viewer = _make_approved_instructor(db, make_user, "dviewer@example.com")
        tpl = _designer_template(db, owner, is_global=True)

        headers = auth_headers(viewer.user_email, viewer._test_password)
        r = client.post(f"/api/v1/certificates/designer/{tpl.id}/duplicate", headers=headers)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"] != tpl.id
        assert body["is_own"] is True
        assert body["is_global"] is False


# =============================================================================
# 4. Delete blocked when referenced
# =============================================================================


class TestDeleteBlockedWhenReferenced:
    def test_delete_blocked_when_course_references_template(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "delcourse@example.com")
        tpl = _designer_template(db, instructor)
        course = _make_course(db, instructor)
        course.certificate_template = str(tpl.id)
        db.commit()

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.delete(f"/api/v1/certificates/designer/{tpl.id}", headers=headers)
        assert r.status_code == 409

    def test_delete_blocked_when_issued_certificate_references_template(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "delissued@example.com")
        tpl = _designer_template(db, instructor)
        issued = IssuedCertificate(
            certificate_id=tpl.id, course_id=1, user_id=instructor.id,
            certificate_hash="x" * 20, secure_certificate_id="Y" * 20,
            certificate_title="t", completion_date=datetime.now(timezone.utc),
        )
        db.add(issued)
        db.commit()

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.delete(f"/api/v1/certificates/designer/{tpl.id}", headers=headers)
        assert r.status_code == 409

    def test_delete_succeeds_when_unreferenced(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "delok@example.com")
        tpl = _designer_template(db, instructor)

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.delete(f"/api/v1/certificates/designer/{tpl.id}", headers=headers)
        assert r.status_code == 200

        r2 = client.get("/api/v1/certificates/designer/", headers=headers)
        assert tpl.id not in [t["id"] for t in r2.json()]

    def test_foreign_instructor_cannot_delete(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "delowner@example.com")
        other = _make_approved_instructor(db, make_user, "delother@example.com")
        tpl = _designer_template(db, owner)

        headers = auth_headers(other.user_email, other._test_password)
        r = client.delete(f"/api/v1/certificates/designer/{tpl.id}", headers=headers)
        assert r.status_code == 404  # not visible to a non-owner, non-global row


# =============================================================================
# 5. elements_config validation matrix
# =============================================================================


class TestElementsConfigValidation:
    def _post(self, client, headers, elements):
        return client.post(
            "/api/v1/certificates/designer/",
            json={"name": "Validation Test", "elements_config": elements},
            headers=headers,
        )

    def test_rejects_non_list(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={"name": "Bad", "elements_config": "not-a-list"},
            headers=headers,
        )
        assert r.status_code == 422

    def test_rejects_unknown_element_type(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val2@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = self._post(client, headers, [{"type": "flying_unicorn", "x": 0, "y": 0, "width": 10, "height": 10}])
        assert r.status_code == 422

    def test_rejects_more_than_100_elements(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val3@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        elements = _simple_elements(101)
        r = self._post(client, headers, elements)
        assert r.status_code == 422

    def test_accepts_exactly_100_elements(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val4@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        elements = _simple_elements(100)
        r = self._post(client, headers, elements)
        assert r.status_code == 201, r.text

    def test_rejects_numeric_field_out_of_bounds(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val5@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = self._post(client, headers, [
            {"type": "text", "content": "hi", "x": 999999999, "y": 0, "width": 10, "height": 10}
        ])
        assert r.status_code == 422

    def test_rejects_non_numeric_position(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val6@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = self._post(client, headers, [
            {"type": "text", "content": "hi", "x": "not-a-number", "y": 0, "width": 10, "height": 10}
        ])
        assert r.status_code == 422

    def test_non_curated_font_falls_back_instead_of_rejecting(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val7@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = self._post(client, headers, [
            {"type": "student_name", "x": 0, "y": 0, "width": 10, "height": 10, "font_family": "Comic Sans MS"}
        ])
        assert r.status_code == 201, r.text
        assert r.json()["elements_config"][0]["font_family"] is None

    def test_curated_font_preserved(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val8@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        font = next(iter(CURATED_FONTS.keys()))
        r = self._post(client, headers, [
            {"type": "student_name", "x": 0, "y": 0, "width": 10, "height": 10, "font_family": font}
        ])
        assert r.status_code == 201, r.text
        assert r.json()["elements_config"][0]["font_family"] == font

    def test_rejects_element_not_an_object(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val9@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = self._post(client, headers, ["not-a-dict"])
        assert r.status_code == 422

    def test_empty_elements_config_accepted(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "val10@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = self._post(client, headers, [])
        assert r.status_code == 201, r.text


# =============================================================================
# 6. Preview endpoint returns a data URI (deterministic via ReportLab
#    fallback when Chrome is unavailable — verified explicitly below).
# =============================================================================


class TestPreviewEndpoint:
    def test_preview_returns_data_uri(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "preview1@example.com")
        tpl = _designer_template(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(f"/api/v1/certificates/designer/{tpl.id}/preview", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["preview_url"].startswith("data:application/pdf;base64,")
        assert body["renderer"] in ("chrome", "reportlab")
        assert body["template_id"] == tpl.id

    def test_preview_falls_back_to_reportlab_without_chrome(self, client, db, make_user, auth_headers, monkeypatch):
        """Explicitly force the Chrome branch to fail (this box has no
        pinned chromedriver / browser — plan note: 'Chrome likely absent on
        this box') and assert the ReportLab fallback still produces a
        deterministic data: URI rather than a 500."""
        instructor = _make_approved_instructor(db, make_user, "preview2@example.com")
        tpl = _designer_template(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        def _boom(*a, **k):
            raise RuntimeError("no chrome on this box")

        monkeypatch.setattr(
            CertificateService, "_render_local_html_pdf_via_chrome", staticmethod(_boom)
        )

        r = client.post(f"/api/v1/certificates/designer/{tpl.id}/preview", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["renderer"] == "reportlab"
        assert body["preview_url"].startswith("data:application/pdf;base64,")

    def test_preview_forbidden_for_foreign_instructor(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "pow@example.com")
        other = _make_approved_instructor(db, make_user, "poth@example.com")
        tpl = _designer_template(db, owner)

        headers = auth_headers(other.user_email, other._test_password)
        r = client.post(f"/api/v1/certificates/designer/{tpl.id}/preview", headers=headers)
        assert r.status_code == 404

    def test_preview_allowed_for_global_template_by_non_owner(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "gpow@example.com")
        viewer = _make_approved_instructor(db, make_user, "gpviewer@example.com")
        tpl = _designer_template(db, owner, is_global=True)

        headers = auth_headers(viewer.user_email, viewer._test_password)
        r = client.post(f"/api/v1/certificates/designer/{tpl.id}/preview", headers=headers)
        assert r.status_code == 200


# =============================================================================
# 7. /certificates/templates/list includes ready builder templates
# =============================================================================


class TestTemplatesListIncludesBuilderTemplates:
    def test_global_builder_template_appears_in_public_list(self, client, db, make_user):
        """M-1 fix: a builder template only appears in the public list once
        an admin has marked it is_global — a private (non-global, no-slug)
        draft must NOT be exposed here (see TestTemplatesListScoping below)."""
        instructor = _make_approved_instructor(db, make_user, "listtpl@example.com")
        tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="", is_global=True)

        r = client.get("/api/v1/certificates/templates/list")
        assert r.status_code == 200
        ids = [row["id"] for row in r.json()]
        assert tpl.id in ids
        row = next(row for row in r.json() if row["id"] == tpl.id)
        assert row["template_type"] == "builder"


# =============================================================================
# 8. Fix round — H-1: image src allowlist (write + render time)
# =============================================================================


class TestImageSrcAllowlist:
    def test_is_safe_asset_src_accepts_uploads_and_certificate_files_and_data_uri(self):
        assert is_safe_asset_src("/uploads/certs/sig.png") is True
        assert is_safe_asset_src("/certificate-files/thumbnails/x.png") is True
        assert is_safe_asset_src("data:image/png;base64,AAAA") is True
        assert is_safe_asset_src("data:image/jpeg;base64,AAAA") is True
        assert is_safe_asset_src("data:image/webp;base64,AAAA") is True

    def test_is_safe_asset_src_rejects_file_blob_and_external_http(self):
        assert is_safe_asset_src("file:///etc/passwd") is False
        assert is_safe_asset_src("file://C:/Windows/System32/config/SAM") is False
        assert is_safe_asset_src("blob:https://example.com/uuid") is False
        assert is_safe_asset_src("https://attacker.example/beacon.png") is False
        assert is_safe_asset_src("http://internal-metadata.local/latest") is False
        assert is_safe_asset_src("") is False
        assert is_safe_asset_src(None) is False

    def test_render_drops_file_src_image_element(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                 "image_url": "file:///etc/passwd"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H1a"))
        assert "file:///etc/passwd" not in html
        assert "cert-el-image" not in html

    def test_render_drops_external_https_src_signature_element(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "signature_image", "x": 0, "y": 0, "width": 100, "height": 100,
                 "image_url": "https://attacker.example/beacon.png"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H1b"))
        assert "attacker.example" not in html
        assert "cert-el-signature" not in html

    def test_render_accepts_data_image_uri(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                 "image_url": "data:image/png;base64,AAAA"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H1c"))
        assert "data:image/png;base64,AAAA" in html
        assert "cert-el-image" in html

    def test_render_accepts_uploads_path(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                 "image_url": "/uploads/certificates/sig123.png"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H1d"))
        assert "/uploads/certificates/sig123.png" in html

    def test_render_drops_unsafe_background_image_but_keeps_page(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="file:///etc/shadow",
            elements_config=[],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H1e"))
        assert "/etc/shadow" not in html
        assert "cert-page" in html  # page still renders

    def test_designer_api_rejects_file_src_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h1write1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Malicious Template",
                "elements_config": [
                    {"type": "signature_image", "x": 0, "y": 0, "width": 100, "height": 100,
                     "image_url": "file:///etc/passwd"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_designer_api_rejects_external_https_src_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h1write2@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Malicious Template 2",
                "elements_config": [
                    {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                     "image_url": "https://attacker.example/beacon.png"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_designer_api_accepts_data_uri_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h1write3@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Fine Template",
                "elements_config": [
                    {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                     "image_url": "data:image/png;base64,AAAA"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text

    def test_designer_api_rejects_unsafe_background_image_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h1write4@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Bad Background",
                "background_image": "file:///etc/passwd",
                "elements_config": [],
            },
            headers=headers,
        )
        assert r.status_code == 422


# =============================================================================
# 8b. Re-review fix round — NEW-1: path normalization + re-assertion
#     (raw prefix match was bypassable via ../, percent-encoding variants,
#     mixed encoding, and backslashes)
# =============================================================================


class TestPathTraversalNormalization:
    def test_rejects_raw_dot_dot_traversal(self):
        assert is_safe_asset_src("/uploads/../../../../etc/passwd") is False
        assert is_safe_asset_src("/uploads/../etc/passwd") is False
        assert is_safe_asset_src("/certificate-files/../../etc/passwd") is False

    def test_rejects_percent_encoded_dot_dot_variants(self):
        assert is_safe_asset_src("/uploads/%2e%2e/%2e%2e/etc/passwd") is False
        assert is_safe_asset_src("/uploads/%2E%2E/%2E%2E/etc/passwd") is False  # uppercase hex
        assert is_safe_asset_src("/uploads/..%2fetc%2fpasswd") is False
        assert is_safe_asset_src("/uploads/%2e%2e%2fetc%2fpasswd") is False

    def test_rejects_double_encoded_dot_dot(self):
        # %252e decodes once to %2e, which decodes again to '.' — the
        # loop-until-stable unquote must catch this, not just a single pass.
        assert is_safe_asset_src("/uploads/%252e%252e/%252e%252e/etc/passwd") is False
        assert is_safe_asset_src("/uploads/%252e%252e%252fetc%252fpasswd") is False

    def test_rejects_mixed_encoding_traversal(self):
        assert is_safe_asset_src("/uploads/..%2f../etc/passwd") is False
        assert is_safe_asset_src("/uploads/%2e./%2e./etc/passwd") is False

    def test_rejects_backslash_variants(self):
        assert is_safe_asset_src("/uploads/..\\..\\etc\\passwd") is False
        assert is_safe_asset_src("/uploads/certs\\..\\..\\secrets.txt") is False

    def test_rejects_unterminated_percent_decoding(self):
        # A literal, un-decodable '%' surviving the unquote loop is treated
        # as unsafe rather than guessed at.
        assert is_safe_asset_src("/uploads/100%sure/x.png") is False

    def test_normal_uploads_path_still_passes(self):
        assert is_safe_asset_src("/uploads/certificates/sig123.png") is True
        assert is_safe_asset_src("/uploads/certs/2026/09/thumb.png") is True

    def test_normal_certificate_files_path_still_passes(self):
        assert is_safe_asset_src("/certificate-files/thumbnails/ivory-classic.png") is True

    def test_data_uri_branch_unaffected_by_path_normalization(self):
        assert is_safe_asset_src("data:image/png;base64,QUJDRA==") is True

    def test_render_drops_traversal_src_at_render_time(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                 "image_url": "/uploads/../../../../etc/passwd"},
                {"type": "signature_image", "x": 0, "y": 0, "width": 100, "height": 100,
                 "image_url": "/uploads/%2e%2e/%2e%2e/etc/shadow"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-NEW1a"))
        assert "/etc/passwd" not in html
        assert "/etc/shadow" not in html
        assert "cert-el-image" not in html
        assert "cert-el-signature" not in html

    def test_render_drops_traversal_background_image_at_render_time(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff",
            background_image="/uploads/../../../../etc/passwd",
            elements_config=[],
        )
        html = build_certificate_html(tpl, sample_values("SEC-NEW1b"))
        assert "/etc/passwd" not in html
        assert "cert-page" in html  # page still renders

    def test_designer_api_rejects_dot_dot_traversal_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "new1write1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Traversal Attempt",
                "elements_config": [
                    {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                     "image_url": "/uploads/../../../../etc/passwd"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_designer_api_rejects_percent_encoded_traversal_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "new1write2@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Encoded Traversal Attempt",
                "elements_config": [
                    {"type": "signature_image", "x": 0, "y": 0, "width": 100, "height": 100,
                     "image_url": "/uploads/%2e%2e%2f%2e%2e%2fetc%2fpasswd"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_designer_api_rejects_backslash_traversal_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "new1write3@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Backslash Traversal Attempt",
                "background_image": "/uploads/..\\..\\etc\\passwd",
                "elements_config": [],
            },
            headers=headers,
        )
        assert r.status_code == 422

    def test_designer_api_still_accepts_normal_uploads_path_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "new1write4@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Fine Template With Real Upload",
                "elements_config": [
                    {"type": "image", "x": 0, "y": 0, "width": 100, "height": 100,
                     "image_url": "/uploads/certificates/legit-sig.png"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["elements_config"][0]["image_url"] == "/uploads/certificates/legit-sig.png"


# =============================================================================
# 8c. Re-review fix round — NEW-2: validate_border OverflowError on "infpx"
# =============================================================================


class TestBorderOverflowGuard:
    def test_validate_border_rejects_inf_width_without_raising(self):
        assert validate_border("infpx solid red") is None
        assert validate_border("-infpx solid red") is None
        assert validate_border("nanpx solid red") is None

    def test_validate_border_dict_form_rejects_inf_width_without_raising(self):
        assert validate_border({"width": float("inf"), "style": "solid", "color": "#000"}) is None
        assert validate_border({"width": float("nan"), "style": "solid", "color": "#000"}) is None

    def test_validate_border_still_accepts_normal_values(self):
        assert validate_border("2px solid #000000") == "2px solid #000000"

    def test_validate_letter_spacing_rejects_inf_without_raising(self):
        assert validate_letter_spacing("inf") is None
        assert validate_letter_spacing(float("inf")) is None
        assert validate_letter_spacing(float("nan")) is None
        assert validate_letter_spacing(2) == "2.0px"

    def test_render_drops_inf_border_without_500(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "border": "infpx solid red"},
                {"type": "rect", "x": 0, "y": 0, "width": 50, "height": 50,
                 "border": "nanpx dashed blue"},
            ],
        )
        # Must not raise (would 500 the endpoint on a real request).
        html = build_certificate_html(tpl, sample_values("SEC-NEW2a"))
        assert "cert-page" in html
        assert "infpx" not in html
        assert "nanpx" not in html

    def test_designer_api_rejects_inf_border_at_write_time_with_422_not_500(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "new2write1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "Overflow Border Attempt",
                "elements_config": [
                    {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                     "border": "infpx solid red"},
                ],
            },
            headers=headers,
        )
        # The border is normalized (dropped to None) at write time, not
        # rejected outright — border isn't in the hard-422 list, it's
        # silently corrected like color/font_weight. The critical assertion
        # is that this is NOT a 500.
        assert r.status_code == 201, r.text
        assert r.json()["elements_config"][0]["border"] is None

    def test_preview_endpoint_survives_inf_border_without_500(
        self, client, db, make_user, auth_headers
    ):
        """End-to-end: a template whose stored elements_config somehow
        carries an inf border (e.g. written before this fix) must not 500
        the public-facing preview endpoint."""
        instructor = _make_approved_instructor(db, make_user, "new2write2@example.com")
        tpl = _designer_template(
            db, instructor,
            elements=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "border": "infpx solid red"},
            ],
        )
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(f"/api/v1/certificates/designer/{tpl.id}/preview", headers=headers)
        assert r.status_code == 200, r.text


# =============================================================================
# 9. Fix round — H-2: CSS-context injection allowlists
# =============================================================================


class TestCssInjectionAllowlists:
    def test_validate_color_accepts_hex_rgba_and_named(self):
        assert validate_color("#fff") == "#fff"
        assert validate_color("#ffffff") == "#ffffff"
        assert validate_color("rgba(0,0,0,0.5)") == "rgba(0,0,0,0.5)"
        assert validate_color("red") == "red"

    def test_validate_color_rejects_injection_payloads(self):
        assert validate_color(";background:url(javascript:alert(1))") is None
        assert validate_color("red; } body { display:none") is None
        assert validate_color("expression(alert(1))") is None
        assert validate_color("url(evil.css)") is None

    def test_validate_font_weight_normalizes(self):
        assert validate_font_weight("bold") == "bold"
        assert validate_font_weight("700") == "700"
        assert validate_font_weight("normal") == "normal"
        assert validate_font_weight("italic;}body{background:url(x)") == "normal"

    def test_validate_letter_spacing_numeric_only(self):
        assert validate_letter_spacing(2) == "2.0px"
        assert validate_letter_spacing("3.5") == "3.5px"
        assert validate_letter_spacing("2px; background:url(x)") is None

    def test_validate_border_decomposes_and_rejects_injection(self):
        assert validate_border("2px solid #000000") == "2px solid #000000"
        assert validate_border({"width": 3, "style": "dashed", "color": "#ff0000"}) == "3px dashed #ff0000"
        # No parseable width/style/color survives — dropped.
        assert validate_border("2px solid red; background:url(javascript:alert(1))") is None or \
            "url(" not in (validate_border("2px solid red; background:url(javascript:alert(1))") or "")

    def test_render_neutralizes_background_color_injection(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "background_color": "red;} body{display:none;} .x{background:url(javascript:alert(1))"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H2a"))
        assert "url(" not in html
        assert "javascript:" not in html
        assert "display:none" not in html.split('<div id="cert-page">')[1]

    def test_render_neutralizes_font_color_injection(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "font_color": "blue; background:url(evil.png); color:red"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H2b"))
        assert "url(evil.png)" not in html
        # font_color falls back to the default black since the payload doesn't
        # match the color allowlist.
        assert "color:#000000" in html

    def test_render_neutralizes_border_injection(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "border": "2px solid red; background:url(javascript:alert(1))"},
                {"type": "rect", "x": 0, "y": 0, "width": 50, "height": 50,
                 "border": "1px solid blue; } * { display:none"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H2c"))
        assert "url(" not in html
        assert "javascript:" not in html
        assert "display:none" not in html

    def test_render_neutralizes_letter_spacing_injection(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "letter_spacing": "2px; background:url(evil.png)"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H2d"))
        assert "url(evil.png)" not in html
        assert "letter-spacing" not in html  # non-numeric spacing dropped entirely

    def test_render_neutralizes_font_weight_injection(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="#ffffff", background_image="",
            elements_config=[
                {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                 "font_weight": "bold; background:url(evil.png)"},
            ],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H2e"))
        assert "url(evil.png)" not in html
        assert "font-weight:normal" in html

    def test_render_neutralizes_page_background_color_injection(self):
        from types import SimpleNamespace

        tpl = SimpleNamespace(
            certificate_width=1400, certificate_height=1000,
            background_color="red;} body{background:url(javascript:alert(1))",
            background_image="", elements_config=[],
        )
        html = build_certificate_html(tpl, sample_values("SEC-H2f"))
        assert "url(" not in html
        assert "javascript:" not in html
        assert "background-color:#ffffff" in html  # fell back to white

    def test_designer_api_normalizes_css_fields_at_write_time(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h2write1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.post(
            "/api/v1/certificates/designer/",
            json={
                "name": "CSS Injection Attempt",
                "elements_config": [
                    {"type": "text", "content": "hi", "x": 0, "y": 0, "width": 100, "height": 40,
                     "font_color": "red;} body{background:url(evil)",
                     "font_weight": "bold;}*{display:none",
                     "letter_spacing": "2px;background:url(x)"},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 201, r.text
        el = r.json()["elements_config"][0]
        assert el["font_color"] is None
        assert el["font_weight"] == "normal"
        assert el["letter_spacing"] is None


# =============================================================================
# 10. Fix round — M-1: /certificates/templates/list scoping
# =============================================================================


class TestTemplatesListScoping:
    def test_private_non_global_template_not_in_anonymous_list(self, client, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "m1priv@example.com")
        private_tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="", is_global=False)

        r = client.get("/api/v1/certificates/templates/list")
        assert r.status_code == 200
        ids = [row["id"] for row in r.json()]
        assert private_tpl.id not in ids

    def test_global_template_visible_in_anonymous_list(self, client, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "m1glob@example.com")
        global_tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="", is_global=True)

        r = client.get("/api/v1/certificates/templates/list")
        assert r.status_code == 200
        ids = [row["id"] for row in r.json()]
        assert global_tpl.id in ids

    def test_legacy_slug_template_visible_in_anonymous_list(self, client, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "m1slug@example.com")
        slug_tpl = _designer_template(db, instructor, elements=[], post_name="ivory-classic", is_global=False)

        r = client.get("/api/v1/certificates/templates/list")
        assert r.status_code == 200
        ids = [row["id"] for row in r.json()]
        assert slug_tpl.id in ids

    def test_private_and_global_and_legacy_mix(self, client, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "m1mix@example.com")
        private_tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="", is_global=False)
        global_tpl = _designer_template(db, instructor, elements=_simple_elements(), post_name="", is_global=True)
        slug_tpl = _designer_template(db, instructor, elements=[], post_name="midnight-gold", is_global=False)

        r = client.get("/api/v1/certificates/templates/list")
        assert r.status_code == 200
        ids = [row["id"] for row in r.json()]
        assert private_tpl.id not in ids
        assert global_tpl.id in ids
        assert slug_tpl.id in ids


# =============================================================================
# 11. Fix round — M-2: designer PUT invalidates rendered caches
# =============================================================================


class TestPutInvalidatesRenderedCaches:
    def test_put_calls_cache_clear_for_referencing_issued_certificates(
        self, client, db, make_user, auth_headers, monkeypatch
    ):
        instructor = _make_approved_instructor(db, make_user, "m2put1@example.com")
        tpl = _designer_template(db, instructor)
        issued = IssuedCertificate(
            certificate_id=tpl.id, course_id=1, user_id=instructor.id,
            certificate_hash="m" * 20, secure_certificate_id="N" * 20,
            certificate_title="t", completion_date=datetime.now(timezone.utc),
        )
        db.add(issued)
        db.commit()

        calls = {"pdf": 0, "png": 0, "webp": 0}

        def _mk(name):
            def _fn(certificate):
                calls[name] += 1
            return _fn

        monkeypatch.setattr(CertificateService, "clear_html_pdf_cache", staticmethod(_mk("pdf")))
        monkeypatch.setattr(CertificateService, "clear_png_cache", staticmethod(_mk("png")))
        monkeypatch.setattr(CertificateService, "clear_webp_cache", staticmethod(_mk("webp")))

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.put(
            f"/api/v1/certificates/designer/{tpl.id}",
            json={"name": "Corrected Design"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert calls["pdf"] == 1
        assert calls["png"] == 1
        assert calls["webp"] == 1

    def test_put_does_not_invalidate_caches_for_unrelated_templates(
        self, client, db, make_user, auth_headers, monkeypatch
    ):
        instructor = _make_approved_instructor(db, make_user, "m2put2@example.com")
        tpl_a = _designer_template(db, instructor)
        tpl_b = _designer_template(db, instructor)
        issued_b = IssuedCertificate(
            certificate_id=tpl_b.id, course_id=1, user_id=instructor.id,
            certificate_hash="p" * 20, secure_certificate_id="Q" * 20,
            certificate_title="t", completion_date=datetime.now(timezone.utc),
        )
        db.add(issued_b)
        db.commit()

        calls = {"n": 0}

        def _fn(certificate):
            calls["n"] += 1

        monkeypatch.setattr(CertificateService, "clear_html_pdf_cache", staticmethod(_fn))
        monkeypatch.setattr(CertificateService, "clear_png_cache", staticmethod(_fn))
        monkeypatch.setattr(CertificateService, "clear_webp_cache", staticmethod(_fn))

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.put(
            f"/api/v1/certificates/designer/{tpl_a.id}",
            json={"name": "Edit A"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert calls["n"] == 0  # tpl_a has no issued certificates


# =============================================================================
# 12. Fix round — L-3: startup purge of stale render temp files
# =============================================================================


class TestRenderTmpPurge:
    def test_purge_removes_files_older_than_max_age(self, tmp_path, monkeypatch):
        import os
        import time

        monkeypatch.setattr(CertificateService, "_render_tmp_dir", staticmethod(lambda: str(tmp_path)))

        old_file = tmp_path / "cert_render_old.html"
        old_file.write_text("<html></html>", encoding="utf-8")
        old_time = time.time() - 7200  # 2h old
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_path / "cert_render_new.html"
        new_file.write_text("<html></html>", encoding="utf-8")

        removed = CertificateService.purge_stale_render_tmp(max_age_seconds=3600)
        assert removed == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_purge_is_a_noop_when_dir_missing(self, tmp_path, monkeypatch):
        missing = tmp_path / "does_not_exist"
        monkeypatch.setattr(CertificateService, "_render_tmp_dir", staticmethod(lambda: str(missing)))
        removed = CertificateService.purge_stale_render_tmp()
        assert removed == 0

    def test_purge_never_raises_on_unexpected_error(self, monkeypatch):
        def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(CertificateService, "_render_tmp_dir", staticmethod(_boom))
        # Must not raise — best-effort per L-3.
        removed = CertificateService.purge_stale_render_tmp()
        assert removed == 0


# =============================================================================
# 13. Fix round — L-2: ReportLab fallback path applies the same src allowlist
# =============================================================================


class TestReportLabFallbackSrcAllowlist:
    def test_render_template_preview_skips_unsafe_image_src(self, tmp_path):
        template_design = {
            "dimensions": {"width": 800, "height": 600},
            "background": {"type": "color", "value": "#ffffff"},
            "elements": [
                {"type": "signature_image", "x": 10, "y": 10, "width": 100, "height": 50,
                 "image_url": "file:///etc/passwd"},
            ],
        }
        sample = {"student_name": "X", "course_title": "Y", "completion_date": "Z"}
        out_path = str(tmp_path / "preview.pdf")
        # Must not raise, and must not attempt to load the file:// path —
        # the element is silently skipped (ReportLab fallback stays
        # deterministic/best-effort, matching every other element type here).
        CertificateService.render_template_preview(template_design, sample, out_path)
        import os
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0

    def test_render_template_preview_allows_safe_image_src_lookup(self, tmp_path, monkeypatch):
        """Confirms the guard calls _load_image_reader only for a safe src —
        proven by monkeypatching _load_image_reader to record its calls."""
        calls = []

        def _fake_loader(url):
            calls.append(url)
            return None

        monkeypatch.setattr(CertificateService, "_load_image_reader", staticmethod(_fake_loader))

        template_design = {
            "dimensions": {"width": 800, "height": 600},
            "background": {"type": "color", "value": "#ffffff"},
            "elements": [
                {"type": "signature_image", "x": 10, "y": 10, "width": 100, "height": 50,
                 "image_url": "/uploads/certs/sig.png"},
                {"type": "image", "x": 10, "y": 10, "width": 100, "height": 50,
                 "image_url": "file:///etc/passwd"},
            ],
        }
        sample = {"student_name": "X", "course_title": "Y", "completion_date": "Z"}
        out_path = str(tmp_path / "preview2.pdf")
        CertificateService.render_template_preview(template_design, sample, out_path)

        assert "/uploads/certs/sig.png" in calls
        assert "file:///etc/passwd" not in calls


# =============================================================================
# Course certificate_id authorization (review finding M1)
# =============================================================================


class TestCourseCertificateIdValidation:
    """A course may only reference a certificate template the caller is
    entitled to use: a legacy (slug) row, a global row, or a designer row the
    caller owns. Admins may reference anything.

    Before this validation an instructor could POST/PUT an arbitrary
    certificate_id — including a colleague's private designer draft that the
    course editor's picker never offers — and issue certificates against
    someone else's design.
    """

    def _course_payload(self, **overrides):
        payload = {
            "title": "Cert Validation Course",
            "description": "d",
            "content": "c",
            "price": 0,
            "level": "beginner",
            "category": "Meiporul",
            "language": "English",
            "duration": 10,
        }
        payload.update(overrides)
        return payload

    def test_create_rejects_other_instructors_private_template(
        self, client, db, make_user, auth_headers
    ):
        owner = _make_approved_instructor(db, make_user, "m1_owner@example.com")
        other = _make_approved_instructor(db, make_user, "m1_other@example.com")
        private_tpl = _designer_template(db, owner)  # not global, no slug

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=private_tpl.id),
            headers=auth_headers("m1_other@example.com"),
        )
        assert r.status_code == 422, r.text

    def test_create_accepts_own_designer_template(
        self, client, db, make_user, auth_headers
    ):
        owner = _make_approved_instructor(db, make_user, "m1_own@example.com")
        own_tpl = _designer_template(db, owner)

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=own_tpl.id),
            headers=auth_headers("m1_own@example.com"),
        )
        assert r.status_code == 200, r.text

    def test_create_accepts_global_template(
        self, client, db, make_user, auth_headers
    ):
        admin = make_user(role="admin", email="m1_admin1@example.com")
        instructor = _make_approved_instructor(db, make_user, "m1_glob@example.com")
        global_tpl = _designer_template(db, admin, is_global=True)

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=global_tpl.id),
            headers=auth_headers("m1_glob@example.com"),
        )
        assert r.status_code == 200, r.text

    def test_create_accepts_legacy_slug_template(
        self, client, db, make_user, auth_headers
    ):
        admin = make_user(role="admin", email="m1_admin2@example.com")
        instructor = _make_approved_instructor(db, make_user, "m1_legacy@example.com")
        legacy_tpl = _designer_template(db, admin, post_name="classic-gold")

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=legacy_tpl.id),
            headers=auth_headers("m1_legacy@example.com"),
        )
        assert r.status_code == 200, r.text

    def test_create_rejects_nonexistent_template(
        self, client, db, make_user, auth_headers
    ):
        _make_approved_instructor(db, make_user, "m1_missing@example.com")

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=99999999),
            headers=auth_headers("m1_missing@example.com"),
        )
        assert r.status_code == 422, r.text

    def test_admin_may_use_any_template(
        self, client, db, make_user, auth_headers
    ):
        from app.core.security import get_password_hash
        from app.models.user import User

        owner = _make_approved_instructor(db, make_user, "m1_owner2@example.com")
        private_tpl = _designer_template(db, owner)

        # Admin logins require the 2FA dance — use the shared helper rather
        # than auth_headers().
        admin = User(
            user_login="m1_admin", user_pass=get_password_hash("Test@123"),
            user_nicename="m1_admin", user_email="m1_admin3@example.com",
            display_name="M1 Admin", role="admin", is_active=True, is_verified=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin._test_password = "Test@123"

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=private_tpl.id),
            headers=_admin_headers(client, db, admin),
        )
        assert r.status_code == 200, r.text

    def test_create_without_certificate_id_is_unaffected(
        self, client, db, make_user, auth_headers
    ):
        _make_approved_instructor(db, make_user, "m1_none@example.com")

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(),
            headers=auth_headers("m1_none@example.com"),
        )
        assert r.status_code == 200, r.text

    def test_update_rejects_other_instructors_private_template(
        self, client, db, make_user, auth_headers
    ):
        owner = _make_approved_instructor(db, make_user, "m1_uowner@example.com")
        other = _make_approved_instructor(db, make_user, "m1_uother@example.com")
        course = _make_course(db, other, title="M1 Update Course")
        private_tpl = _designer_template(db, owner)

        r = client.put(
            f"/api/v1/courses/{course.id}",
            json={"certificate_id": private_tpl.id},
            headers=auth_headers("m1_uother@example.com"),
        )
        assert r.status_code == 422, r.text

    def test_update_accepts_own_designer_template(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "m1_uown@example.com")
        course = _make_course(db, instructor, title="M1 Update Course 2")
        own_tpl = _designer_template(db, instructor)

        r = client.put(
            f"/api/v1/courses/{course.id}",
            json={"certificate_id": own_tpl.id},
            headers=auth_headers("m1_uown@example.com"),
        )
        assert r.status_code == 200, r.text
        db.refresh(course)
        assert course.certificate_template == str(own_tpl.id)

    def test_update_clearing_certificate_is_allowed(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "m1_uclear@example.com")
        course = _make_course(db, instructor, title="M1 Update Course 3")

        r = client.put(
            f"/api/v1/courses/{course.id}",
            json={"certificate_id": None},
            headers=auth_headers("m1_uclear@example.com"),
        )
        assert r.status_code == 200, r.text

    # -- out-of-range ids (review finding NEW-1) ----------------------------
    # Python ints are unbounded but the id column is a 32-bit INTEGER, so an
    # oversized value reaches the driver and raises OverflowError — surfacing
    # as an uncaught 500 rather than the 422 this validation exists to give.

    @pytest.mark.parametrize("oversized", [10**20, 2**63])
    def test_create_rejects_oversized_certificate_id(
        self, client, db, make_user, auth_headers, oversized
    ):
        _make_approved_instructor(db, make_user, f"m1_big{oversized}@example.com")

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=oversized),
            headers=auth_headers(f"m1_big{oversized}@example.com"),
        )
        assert r.status_code == 422, r.text

    @pytest.mark.parametrize("oversized", [10**20, 2**63])
    def test_update_rejects_oversized_certificate_id(
        self, client, db, make_user, auth_headers, oversized
    ):
        instructor = _make_approved_instructor(
            db, make_user, f"m1_ubig{oversized}@example.com"
        )
        course = _make_course(db, instructor, title=f"M1 Big {oversized}")

        r = client.put(
            f"/api/v1/courses/{course.id}",
            json={"certificate_id": oversized},
            headers=auth_headers(f"m1_ubig{oversized}@example.com"),
        )
        assert r.status_code == 422, r.text

    def test_negative_certificate_id_is_rejected(
        self, client, db, make_user, auth_headers
    ):
        _make_approved_instructor(db, make_user, "m1_neg@example.com")

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=-1),
            headers=auth_headers("m1_neg@example.com"),
        )
        assert r.status_code == 422, r.text

    def test_max_int32_id_still_takes_the_not_found_path(
        self, client, db, make_user, auth_headers
    ):
        """The upper bound is inclusive — a valid-range id that simply does
        not exist must still 422 as 'not found', not be rejected as
        malformed, and must never reach the driver as an overflow."""
        _make_approved_instructor(db, make_user, "m1_maxint@example.com")

        r = client.post(
            "/api/v1/courses/",
            json=self._course_payload(certificate_id=2**31 - 1),
            headers=auth_headers("m1_maxint@example.com"),
        )
        assert r.status_code == 422, r.text
