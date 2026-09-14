"""Security-audit fixes (2026-08-19) — regressions for task 1.

Covered findings:

* federated login accepted any signature-valid Firebase token: unverified
  emails and non-Google providers of the same Firebase project reached
  account lookup and token minting (``_validate_federated_claims`` gate);
* Google sign-in minted full tokens for TOTP-enrolled accounts — a 2FA
  bypass relative to /login (pending-2FA parity: 401 ``otp_required``);
* VIDEO_SECRET could ship to production as the repo default, making the
  stream-token enrollment gate forgeable (import-time fail fast);
* the login rate limiter never engaged on real traffic (path match missed
  the mounted prefix / trailing slash) and keyed buckets on the FIRST
  X-Forwarded-For entry, which is client-spoofable;
* certificate verify/view pages interpolated unescaped student/course/
  instructor names into public HTML (stored XSS);
* login errors distinguished "no account" from "wrong password"
  (user enumeration);
* password-reset tokens were replayable and accepted weak passwords;
* /stream/extract passed the raw URL to yt-dlp and interpolated an
  unvalidated quality (SSRF / format-selector injection);
* /extract/video ran yt-dlp for anonymous callers with no concurrency cap;
* chunked uploads assembled any extension into the served /uploads tree
  and never enforced the declared file_size while chunks arrived;
* player /stream-url read a non-existent Lesson column (500 on every call).
"""

import json
import time
import types
from datetime import datetime, timezone

import pytest
import pyotp
from fastapi import HTTPException

from app.core import totp
from app.models.certificate import IssuedCertificate
from app.models.course import Course, Lesson
from app.models.user import InstructorProfile


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_course(db, instructor, title="Course"):
    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="",
        post_excerpt="",
        post_status="published",
        post_name="course",
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


def _make_lesson(db, instructor, course, title="Lesson", video_url=""):
    lesson = Lesson(
        post_author=instructor.id,
        post_title=title,
        post_parent=course.id,
        lesson_video_url=video_url,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _enable_totp(db, user):
    user.totp_enabled = True
    user.totp_secret = totp.generate_secret()
    db.commit()
    return user


@pytest.fixture
def firebase_ok(monkeypatch):
    """Replace the Firebase signature-verification boundary with a fixed
    decoded-token factory (same boundary the existing tests mock). Returns
    a callable so individual tests can vary the claims."""
    import app.routers.auth as auth_module

    def _install(claims=None):
        claims = claims or {}

        def _fake_verify(id_token: str) -> dict:
            token = {
                "email": claims.get("email", "google-user@example.com"),
                "name": claims.get("name", "Google User"),
                "user_id": claims.get("user_id", "firebase-uid-1"),
                "sub": claims.get("sub", "firebase-uid-1"),
                "picture": "",
                "email_verified": claims.get("email_verified", True),
                "firebase": claims.get(
                    "firebase", {"sign_in_provider": "google.com"}
                ),
            }
            return token

        monkeypatch.setattr(auth_module, "verify_firebase_token", _fake_verify)

    return _install


# ---------------------------------------------------------------------------
# Item 1a — federated claim gate
# ---------------------------------------------------------------------------


def test_federated_claims_accept_verified_google_token(firebase_ok):
    from app.routers.auth import _validate_federated_claims

    _validate_federated_claims(
        {"email_verified": True, "firebase": {"sign_in_provider": "google.com"}}
    )  # no raise


def test_federated_claims_reject_unverified_email():
    from app.routers.auth import _validate_federated_claims

    with pytest.raises(HTTPException) as exc:
        _validate_federated_claims(
            {"email_verified": False, "firebase": {"sign_in_provider": "google.com"}}
        )
    assert exc.value.status_code == 403


def test_federated_claims_reject_missing_email_verified():
    from app.routers.auth import _validate_federated_claims

    # Missing claim (and truthy-but-not-True values like "true") must fail —
    # only an exact boolean True passes.
    with pytest.raises(HTTPException) as exc:
        _validate_federated_claims({"firebase": {"sign_in_provider": "google.com"}})
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException):
        _validate_federated_claims(
            {"email_verified": "true", "firebase": {"sign_in_provider": "google.com"}}
        )


def test_federated_claims_reject_provider_outside_allowlist():
    from app.routers.auth import _validate_federated_claims

    for provider in ("password", "phone", "anonymous", "custom", None):
        with pytest.raises(HTTPException) as exc:
            _validate_federated_claims(
                {"email_verified": True, "firebase": {"sign_in_provider": provider}}
            )
        assert exc.value.status_code == 403


def test_federated_claims_reject_missing_firebase_claim():
    from app.routers.auth import _validate_federated_claims

    with pytest.raises(HTTPException) as exc:
        _validate_federated_claims({"email_verified": True})
    assert exc.value.status_code == 403


def test_google_login_rejects_unverified_email_before_lookup(client, db, make_user, firebase_ok):
    """The claim gate fires BEFORE any account lookup: even a token for a
    known email with email_verified=False must 403, never mint tokens."""
    make_user(email="google-user@example.com")
    firebase_ok({"email_verified": False})

    r = client.post("/api/v1/auth/google", json={"token": "sig-valid-but-unverified"})
    assert r.status_code == 403, r.text
    assert "not verified" in r.json()["detail"]


def test_google_login_rejects_non_google_provider(client, db, make_user, firebase_ok):
    make_user(email="google-user@example.com")
    firebase_ok({"firebase": {"sign_in_provider": "password"}})

    r = client.post("/api/v1/auth/google", json={"token": "t"})
    assert r.status_code == 403, r.text
    assert "provider" in r.json()["detail"].lower()


def test_google_complete_rejects_unverified_email(client, db, make_user, firebase_ok):
    """The /google/complete endpoint enforces the same claim gate."""
    make_user(email="google-user@example.com")
    firebase_ok({"email_verified": False})

    r = client.post(
        "/api/v1/auth/google/complete",
        json={"google_token": "t", "role": "student", "phone": "9876543210"},
    )
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# Item 1b — TOTP parity on the federated path
# ---------------------------------------------------------------------------


def test_totp_enabled_user_via_google_gets_pending_2fa_not_tokens(
    client, db, make_user, firebase_ok
):
    """A TOTP-enrolled account signing in via Google must receive the SAME
    pending-2FA response the password path issues — 401, detail
    'otp_required', Bearer challenge header — and NO access/refresh tokens."""
    user = _enable_totp(db, make_user(email="google-user@example.com"))
    firebase_ok()

    r = client.post("/api/v1/auth/google", json={"token": "t"})

    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "otp_required"
    assert r.headers["www-authenticate"] == "Bearer"
    # No tokens are minted at this stage.
    assert "access_token" not in r.json()
    assert "refresh_token" not in r.json()


def test_totp_enabled_user_via_google_completes_with_code(client, db, make_user, firebase_ok):
    """Re-submitting with the current code completes the login — the same
    inline-verification step the password flow uses."""
    user = _enable_totp(db, make_user(email="google-user@example.com"))
    firebase_ok()

    r = client.post(
        "/api/v1/auth/google",
        json={"token": "t", "otp_code": pyotp.TOTP(user.totp_secret).now()},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "google-user@example.com"


def test_totp_enabled_user_via_google_rejects_bad_code(client, db, make_user, firebase_ok):
    user = _enable_totp(db, make_user(email="google-user@example.com"))
    firebase_ok()

    r = client.post("/api/v1/auth/google", json={"token": "t", "otp_code": "000000"})
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "Invalid authentication code. Please try again."
    assert "access_token" not in r.json()


def test_admin_without_totp_cannot_login_via_google(client, db, make_user, firebase_ok):
    """Privileged accounts are held to the password path's stricter rule:
    admin/superadmin without TOTP enrolled are refused outright."""
    make_user(role="admin", email="google-admin@example.com")
    firebase_ok({"email": "google-admin@example.com"})

    r = client.post("/api/v1/auth/google", json={"token": "t"})
    assert r.status_code == 403, r.text
    assert "Two-factor authentication is required" in r.json()["detail"]


def test_google_complete_existing_user_with_totp_requires_code(client, db, make_user, firebase_ok):
    """The race-fallback branch of /google/complete (account appeared after
    /google) must clear the same 2FA challenge before minting."""
    _enable_totp(db, make_user(email="google-user@example.com"))
    firebase_ok()

    r = client.post(
        "/api/v1/auth/google/complete",
        json={"google_token": "t", "role": "student", "phone": "9876543210"},
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "otp_required"


# ---------------------------------------------------------------------------
# Item 2 — VIDEO_SECRET fail-fast in production
# ---------------------------------------------------------------------------


def test_default_video_secret_rejected_in_production():
    from app.routers.player import validate_video_secret

    with pytest.raises(RuntimeError, match="VIDEO_SECRET"):
        validate_video_secret("sasha-video-secret-change-this", "production")


def test_empty_video_secret_rejected_in_production():
    from app.routers.player import validate_video_secret

    with pytest.raises(RuntimeError, match="VIDEO_SECRET"):
        validate_video_secret("", "production")


def test_default_video_secret_allowed_in_development_and_tests():
    from app.routers.player import validate_video_secret

    validate_video_secret("sasha-video-secret-change-this", "development")  # no raise
    validate_video_secret("sasha-video-secret-change-this", "test")  # no raise


def test_real_video_secret_allowed_in_production():
    from app.routers.player import validate_video_secret

    validate_video_secret("a-real-random-secret", "production")  # no raise


# ---------------------------------------------------------------------------
# Item 3 — login-path matcher + X-Forwarded-For parsing
# ---------------------------------------------------------------------------


def test_login_path_matcher_covers_all_traffic_shapes():
    from app.core.security_middleware import is_login_path

    for path in (
        "/auth/login",
        "/auth/login/",
        "/api/v1/auth/login",
        "/api/v1/auth/login/",
    ):
        assert is_login_path(path), path


def test_login_path_matcher_rejects_lookalikes():
    from app.core.security_middleware import is_login_path

    for path in (
        "/auth/logout",
        "/auth/register",
        "/api/v1/auth/loginx",
        "/api/v1/auth/login-other",
        "/auth/login/otp",  # subpaths are NOT the login endpoint
        "/health",
        "",
        "/",
    ):
        assert not is_login_path(path), path


def test_xff_parsing_takes_last_entry():
    from app.core.security_middleware import last_forwarded_ip

    # The rightmost entry is appended by OUR trusted proxy; the leftmost is
    # whatever the client chose to prepend.
    assert (
        last_forwarded_ip("1.2.3.4, 10.0.0.1, 172.17.0.5") == "172.17.0.5"
    )
    assert last_forwarded_ip("1.2.3.4,10.0.0.1") == "10.0.0.1"
    assert last_forwarded_ip("9.9.9.9") == "9.9.9.9"


def test_xff_parsing_handles_degenerate_headers():
    from app.core.security_middleware import last_forwarded_ip

    assert last_forwarded_ip(None) is None
    assert last_forwarded_ip("") is None
    assert last_forwarded_ip(",,") is None
    # Trailing comma with junk entries only: fall back to the last REAL one.
    assert last_forwarded_ip("1.2.3.4, ") == "1.2.3.4"


def test_rate_limiter_get_client_ip_uses_last_xff_entry():
    """The rate-limiting middleware itself must key buckets on the proxy-
    appended entry, not the client-controlled first one."""
    from app.core.security_middleware import RateLimitMiddleware

    mw = RateLimitMiddleware.__new__(RateLimitMiddleware)  # skip redis __init__
    request = types.SimpleNamespace(
        headers={"X-Forwarded-For": "6.6.6.6, 10.0.0.9"},
        client=types.SimpleNamespace(host="127.0.0.1"),
    )
    assert mw._get_client_ip(request) == "10.0.0.9"

    # No XFF: fall back to X-Real-IP, then the socket address.
    request = types.SimpleNamespace(
        headers={"X-Real-IP": "10.0.0.8"}, client=types.SimpleNamespace(host="127.0.0.1")
    )
    assert mw._get_client_ip(request) == "10.0.0.8"

    request = types.SimpleNamespace(headers={}, client=types.SimpleNamespace(host="127.0.0.1"))
    assert mw._get_client_ip(request) == "127.0.0.1"


# ---------------------------------------------------------------------------
# Item 4 — certificate HTML escaping (stored XSS)
# ---------------------------------------------------------------------------


XSS_NAME = '<img src=x onerror="alert(document.cookie)">'
ESCAPED_NAME = "&lt;img src=x onerror=&quot;alert(document.cookie)&quot;&gt;"


@pytest.fixture
def xss_template(monkeypatch, tmp_path):
    """Point template resolution at a synthetic template carrying the same
    sentinels the production templates use."""
    import app.routers.certificates as certs

    template = tmp_path / "template.html"
    template.write_text(
        "<html><body>"
        "<div class='student'>Student Name</div>"
        "<div class='student2'>Logadheenan V M</div>"
        "<div class='course'>Course Title</div>"
        "<div class='course2'>Full-Stack Web Development</div>"
        "<div class='instructor'>Instructor Name</div>"
        "<div class='instructor2'>Gayathri Devi</div>"
        "<div class='date'>June 02, 2026</div>"
        "<div id=\"certId\">CERT-2026-000142</div>"
        "</body></html>",
        encoding="utf-8",
    )
    monkeypatch.setattr(certs, "resolve_template_path", lambda db, cert: template)
    return template


def _make_certificate(db, instructor, student, course):
    cert = IssuedCertificate(
        certificate_id=0,  # no template row -> default template resolution
        course_id=course.id,
        user_id=student.id,
        certificate_hash="cafebabecafebabecafebabecafebabe",
        secure_certificate_id="SECURE123",
        certificate_title="Cert",
        completion_date=datetime.now(timezone.utc),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


def test_certificate_view_escapes_xss_display_name(
    client, db, make_user, xss_template, monkeypatch
):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(email="student@example.com")
    course = _make_course(db, instructor, title="<script>alert(1)</script> Course")
    # The XSS payload rides on the student display name.
    student.display_name = XSS_NAME
    db.commit()
    cert = _make_certificate(db, instructor, student, course)

    r = client.get(f"/api/v1/certificates/view/{cert.id}")
    assert r.status_code == 200, r.text
    html = r.text

    assert XSS_NAME not in html  # raw payload never rendered
    assert ESCAPED_NAME in html  # escaped form present
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; Course" in html


def test_certificate_verify_page_escapes_xss_display_name(
    client, db, make_user, xss_template
):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(email="student@example.com")
    course = _make_course(db, instructor)
    student.display_name = XSS_NAME
    db.commit()
    cert = _make_certificate(db, instructor, student, course)

    # ?full=1 renders the heavy template path with the same substitutions.
    r = client.get(
        "/api/v1/certificates/verify-certificate",
        params={"id": cert.secure_certificate_id, "hash": cert.certificate_hash, "full": 1},
    )
    assert r.status_code == 200, r.text
    assert XSS_NAME not in r.text
    assert ESCAPED_NAME in r.text


def test_instructor_name_is_escaped_too(client, db, make_user, xss_template):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(email="student@example.com")
    course = _make_course(db, instructor)
    instructor.display_name = XSS_NAME
    db.commit()
    cert = _make_certificate(db, instructor, student, course)

    r = client.get(f"/api/v1/certificates/view/{cert.id}")
    assert r.status_code == 200, r.text
    assert XSS_NAME not in r.text
    assert r.text.count(ESCAPED_NAME) >= 2  # student + instructor slots


# ---------------------------------------------------------------------------
# Item 5 — login enumeration
# ---------------------------------------------------------------------------


def test_login_unknown_email_and_wrong_password_are_indistinguishable(client, db, make_user):
    make_user(email="known@example.com", password="Test@123")

    r_unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}
    )
    r_wrong = client.post(
        "/api/v1/auth/login", json={"email": "known@example.com", "password": "Wrong@999"}
    )

    assert r_unknown.status_code == 401
    assert r_wrong.status_code == 401
    # Identical message and shape — no oracle for account existence.
    assert r_unknown.json() == r_wrong.json()
    assert r_unknown.json()["detail"] == "Invalid email or password"


def test_login_generic_message_does_not_leak_in_headers(client, db, make_user):
    make_user(email="known@example.com")
    r = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"}
    )
    assert r.status_code == 401
    assert "no account" not in r.text.lower()
    assert "incorrect password" not in r.text.lower()


# ---------------------------------------------------------------------------
# Item 6 — password reset single-use + complexity
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_reset_tokens(monkeypatch):
    import app.routers.auth as auth_module

    tokens = []

    async def _capture(email, token):
        tokens.append(token)

    monkeypatch.setattr(auth_module, "send_password_reset_email", _capture)
    return tokens


def test_reset_token_is_single_use(client, db, make_user, captured_reset_tokens):
    user = make_user(email="reset@example.com")
    old_hash = user.user_pass

    r = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200, r.text
    assert len(captured_reset_tokens) == 1
    token = captured_reset_tokens[0]

    # First use succeeds and actually changes the password.
    r1 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassw0rd"},
    )
    assert r1.status_code == 200, r1.text

    db.expire_all()
    fresh = db.query(type(user)).filter_by(id=user.id).one()
    assert fresh.user_pass != old_hash
    # The stored marker was consumed.
    assert fresh.user_activation_key == ""

    # Login with the new password works.
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "NewPassw0rd"},
    )
    assert r_login.status_code == 200, r_login.text

    # REPLAY of the same (still-unexpired JWT) token is rejected.
    r2 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass1"},
    )
    assert r2.status_code == 400, r2.text
    assert "already used" in r2.json()["detail"]

    # And the password was NOT changed by the replay.
    db.expire_all()
    still = db.query(type(user)).filter_by(id=user.id).one()
    assert still.user_pass == fresh.user_pass


def test_reset_superseded_by_newer_token(client, db, make_user, captured_reset_tokens):
    """Requesting a second reset link invalidates the first."""
    make_user(email="reset2@example.com")

    client.post("/api/v1/auth/forgot-password", json={"email": "reset2@example.com"})
    first = captured_reset_tokens[0]
    client.post("/api/v1/auth/forgot-password", json={"email": "reset2@example.com"})
    second = captured_reset_tokens[1]

    r_old = client.post(
        "/api/v1/auth/reset-password",
        json={"token": first, "new_password": "NewPassw0rd"},
    )
    assert r_old.status_code == 400  # superseded

    r_new = client.post(
        "/api/v1/auth/reset-password",
        json={"token": second, "new_password": "NewPassw0rd"},
    )
    assert r_new.status_code == 200


def test_reset_rejects_weak_password(client, db, make_user, captured_reset_tokens):
    make_user(email="reset3@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "reset3@example.com"})
    token = captured_reset_tokens[0]

    # Same complexity rules as RegisterRequest: 8+ chars, upper, lower, digit.
    for weak in ("short1A", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere"):
        r = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": weak},
        )
        assert r.status_code == 422, weak

    # The token was NOT consumed by a rejected request — it still works.
    r_ok = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "StrongPass1"},
    )
    assert r_ok.status_code == 200, r_ok.text


# ---------------------------------------------------------------------------
# Item 7 — /stream/extract SSRF canonicalization
# ---------------------------------------------------------------------------


def test_canonical_url_from_wellformed_youtube_urls():
    from app.routers.video_streaming import canonical_youtube_watch_url

    for url in (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&list=xyz",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ):
        assert (
            canonical_youtube_watch_url(url)
            == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ), url


def test_canonicalization_rejects_ssrf_wrapped_urls():
    from app.routers.video_streaming import canonical_youtube_watch_url

    for url in (
        # Real host is attacker-controlled and the extracted "id" is junk —
        # must be rejected outright.
        "http://evil.com/proxy?u=https://youtube.com/watch?v=evil.com/steal",
        # Id is not 11 plain chars — path/userinfo junk glued on.
        "https://youtu.be/dQw4w9WgXcQ/extra/path",
        "https://youtube.com/watch?v=dQw4w9WgXcQ@evil.com",
        # Wrong length / charset.
        "https://youtube.com/watch?v=short",
        "https://youtube.com/watch?v=dQw4w9WgXcQQ",
        "not a url at all",
    ):
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            canonical_youtube_watch_url(url)


def test_canonicalization_sanitizes_wrapped_url_to_canonical_form():
    """A wrapped URL whose embedded id happens to be a valid 11-char id is
    SANITIZED: only the rebuilt canonical watch URL ever leaves the
    validator — the attacker-controlled host is dropped on the floor."""
    from app.routers.video_streaming import canonical_youtube_watch_url

    assert (
        canonical_youtube_watch_url(
            "http://evil.com/proxy?u=https://youtube.com/watch?v=dQw4w9WgXcQ"
        )
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_extract_quality_allowlist():
    from app.routers.video_streaming import validate_extract_quality

    for q in ("360", "480", "720", "1080", "1440"):
        assert validate_extract_quality(q) == q

    for q in ("720p", "0", "99999", "100;rm -rf /", "best[ext=mp4]", "", None):
        with pytest.raises(ValueError):
            validate_extract_quality(q)


def test_stream_extract_endpoint_rejects_ssrf_url(client, db, make_user, auth_headers):
    """Through the API: an attacker URL with a junk id is 400 at the gate,
    never handed to yt-dlp."""
    make_user(email="student@example.com")
    headers = auth_headers("student@example.com")

    r = client.get(
        "/api/v1/stream/extract",
        params={"url": "https://evil.com/steal?v=evil.com/steal#https://youtube.com/watch?v=x"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "Invalid YouTube URL"


def test_stream_extract_endpoint_sanitizes_to_canonical_url(
    client, db, make_user, auth_headers, monkeypatch
):
    """End-to-end sanitization: an enrolled student passes a WRAPPED url
    (attacker host, valid id); yt-dlp must receive only the REBUILT
    canonical watch URL, never the raw input."""
    import app.routers.video_streaming as vs

    captured = {}

    class _FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            captured["url"] = url
            return {
                "url": "https://cdn.example/stream.mp4",
                "title": "T",
                "duration": 42,
                "height": 720,
                "thumbnail": "",
                "uploader": "someone",
            }

    monkeypatch.setattr(vs.yt_dlp, "YoutubeDL", _FakeYDL)

    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(email="student@example.com")
    course = _make_course(db, instructor)
    db.add(Lesson(
        post_author=instructor.id,
        post_title="Lesson",
        post_parent=course.id,
        lesson_youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ))
    from app.models.enrollment import Enrollment

    db.add(Enrollment(user_id=student.id, course_id=course.id))
    db.commit()
    headers = auth_headers("student@example.com")

    r = client.get(
        "/api/v1/stream/extract",
        params={"url": "http://evil.com/proxy?u=https://youtube.com/watch?v=dQw4w9WgXcQ"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert captured["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert r.json()["data"]["videoId"] == "dQw4w9WgXcQ"


def test_stream_extract_endpoint_rejects_bad_quality(client, db, make_user, auth_headers):
    make_user(email="student@example.com")
    headers = auth_headers("student@example.com")

    r = client.get(
        "/api/v1/stream/extract",
        params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": "720;evil"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "Invalid quality"


# ---------------------------------------------------------------------------
# Item 8 — /extract/video auth + concurrency cap
# ---------------------------------------------------------------------------


def test_extract_video_requires_authentication(client):
    r = client.get("/api/v1/extract/video", params={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 401, r.text

    # A malformed Authorization header must not sneak through either.
    r2 = client.get(
        "/api/v1/extract/video",
        params={"url": "https://youtu.be/dQw4w9WgXcQ"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r2.status_code == 401, r2.text


def test_extract_video_semaphore_configuration():
    """The module-level cap exists and matches the intended bound."""
    from app.routers import video as video_module

    assert video_module.MAX_CONCURRENT_EXTRACTIONS == 4
    # A fresh semaphore must have all permits free.
    fresh = type(video_module._extraction_semaphore)(4)
    assert not fresh.locked()


# ---------------------------------------------------------------------------
# Item 9 — chunked upload whitelist + byte overshoot
# ---------------------------------------------------------------------------


class _MockRedisStore:
    """Async in-memory stand-in for the Redis client (MockRedis semantics)."""

    def __init__(self):
        self.data = {}

    async def ping(self):
        return b"PONG"

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, **kwargs):
        self.data[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.data[key] = value
        return True

    async def delete(self, key):
        self.data.pop(key, None)
        return True

    async def ttl(self, key):
        return 3600


@pytest.fixture
def chunked_env(monkeypatch, tmp_path):
    """Point the chunked router at a fake Redis and a temp upload dir."""
    import app.routers.chunked_upload as cu

    store = _MockRedisStore()

    async def _fake_redis():
        return store

    monkeypatch.setattr(cu, "_redis", _fake_redis)
    monkeypatch.setattr(cu, "_upload_dir", lambda: str(tmp_path))
    return types.SimpleNamespace(store=store, tmp_path=tmp_path, cu=cu)


@pytest.fixture
def instructor_headers(client, db, make_user, auth_headers):
    instructor = make_user(role="instructor", email="chunked-instructor@example.com")
    db.add(InstructorProfile(
        user_id=instructor.id,
        instructor_bio="",
        instructor_designation="",
        is_approved=True,
        is_blocked=False,
    ))
    db.commit()
    return auth_headers("chunked-instructor@example.com")


def _init_upload(client, headers, **overrides):
    payload = {
        "filename": "photo.png",
        "file_size": 10,
        "content_type": "image/png",
        "total_chunks": 1,
        "upload_type": "image",
    }
    payload.update(overrides)
    return client.post(
        "/api/v1/upload/chunked/init", data=payload, headers=headers
    )


def test_chunked_html_via_image_type_rejected_at_init(client, chunked_env, instructor_headers):
    r = _init_upload(
        client,
        instructor_headers,
        filename="evil.html",
        content_type="text/html",
    )
    assert r.status_code == 400, r.text
    assert ".html" in r.json()["detail"]


def test_chunked_content_type_mismatch_rejected_at_init(client, chunked_env, instructor_headers):
    # .png extension but a text/html content type: both must agree.
    r = _init_upload(client, instructor_headers, content_type="text/html")
    assert r.status_code == 400, r.text


def test_chunked_complete_rejects_html_even_for_crafted_session(
    client, db, chunked_env, instructor_headers
):
    """/complete is the AUTHORITATIVE gate: even a session that skipped /init
    validation (crafted straight into the store) cannot land an .html under
    the served /uploads tree."""
    cu = chunked_env.cu
    # Simulate a session written straight into the store (skipping /init's
    # fail-fast check): /complete must still refuse to assemble it.
    profile = db.query(InstructorProfile).order_by(InstructorProfile.id.desc()).first()

    upload_id = "crafted-session-id"
    payload = b"<html><body>xss</body></html>"
    temp_dir = cu._temp_dir_for(upload_id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "chunk_00000").write_bytes(payload)

    chunked_env.store.data[cu._session_key(upload_id)] = json.dumps({
        "upload_id": upload_id,
        "filename": "evil.html",
        "file_size": len(payload),
        "content_type": "text/html",
        "total_chunks": 1,
        "upload_type": "image",
        "user_id": profile.user_id,
        "received_chunks": [0],
        "temp_dir": str(temp_dir),
        "created_at": "2026-08-19T00:00:00",
    })

    r = client.post(
        "/api/v1/upload/chunked/complete",
        data={"upload_id": upload_id},
        headers=instructor_headers,
    )
    assert r.status_code == 400, r.text
    assert ".html" in r.json()["detail"]
    # Nothing was assembled into the upload tree.
    assert not list((chunked_env.tmp_path).rglob("*.html"))


def test_chunked_overshoot_rejected_during_chunk(client, chunked_env, instructor_headers):
    r = _init_upload(client, instructor_headers, file_size=10, total_chunks=1)
    assert r.status_code == 200, r.text
    upload_id = r.json()["upload_id"]

    # 30 bytes against a declared file_size of 10: rejected at /chunk, the
    # chunk file rolled back — not absorbed silently for /complete to find.
    r_chunk = client.post(
        "/api/v1/upload/chunked/chunk",
        data={"upload_id": upload_id, "chunk_number": "0", "total_chunks": "1"},
        files={"chunk": ("chunk_0", b"x" * 30, "application/octet-stream")},
        headers=instructor_headers,
    )
    assert r_chunk.status_code == 400, r_chunk.text
    assert "exceeds declared file size" in r_chunk.json()["detail"]
    assert not list(chunked_env.tmp_path.rglob("chunk_*"))

    # A size-conforming chunk is still accepted afterwards.
    r_ok = client.post(
        "/api/v1/upload/chunked/chunk",
        data={"upload_id": upload_id, "chunk_number": "0", "total_chunks": "1"},
        files={"chunk": ("chunk_0", b"x" * 10, "application/octet-stream")},
        headers=instructor_headers,
    )
    assert r_ok.status_code == 200, r_ok.text

    # And the full round-trip assembles the file.
    r_done = client.post(
        "/api/v1/upload/chunked/complete",
        data={"upload_id": upload_id},
        headers=instructor_headers,
    )
    assert r_done.status_code == 200, r_done.text
    assert r_done.json()["file_url"].startswith("/uploads/images/")
    assert r_done.json()["file_url"].endswith(".png")


# ---------------------------------------------------------------------------
# Item 10 — player stream-url column fix
# ---------------------------------------------------------------------------


def test_stream_url_404s_cleanly_for_lesson_without_video(client, db, make_user):
    """/stream-url used to read `lesson.video_url` — an attribute the Lesson
    model doesn't even have — so every call 500'd with AttributeError."""
    from app.routers import player as player_module

    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(email="student@example.com")
    course = _make_course(db, instructor)
    lesson = _make_lesson(db, instructor, course, video_url="")  # no video

    token = player_module.make_token(student.id, lesson.id)
    r = client.get("/api/v1/video/stream-url", params={"token": token})
    # 404 (the app-wide handler masks the detail text with "Endpoint not
    # found"); before the fix this was an AttributeError 500.
    assert r.status_code == 404, r.text


def test_stream_url_reads_lesson_video_url_column(client, db, make_user, monkeypatch):
    """Happy path reads the real column (cache pre-warmed so the test never
    spawns yt-dlp)."""
    from app.routers import player as player_module

    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(email="student@example.com")
    course = _make_course(db, instructor)
    lesson = _make_lesson(
        db, instructor, course, video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )

    async def _fail_if_called(url):
        raise AssertionError("yt-dlp must not run when the cache is warm")

    monkeypatch.setattr(player_module, "get_stream_url", _fail_if_called)
    player_module.url_cache[lesson.id] = {
        "url": "https://cdn.example/stream.mp4",
        "expires": time.time() + 3600,
    }
    try:
        token = player_module.make_token(student.id, lesson.id)
        r = client.get("/api/v1/video/stream-url", params={"token": token})
        assert r.status_code == 200, r.text
        assert r.json()["url"] == "https://cdn.example/stream.mp4"
        assert r.json()["cached"] is True
    finally:
        player_module.url_cache.pop(lesson.id, None)
