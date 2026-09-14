"""
SashaInfinity LMS Backend - FastAPI Application
Premium Learning Management System
"""

from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from html import escape
from app.core.cors import setup_cors
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import uvicorn
import asyncio
import logging
import os
import re
import json
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, get_db, SessionLocal
from app.core.redis import init_redis

# Import all models to ensure they are registered with SQLAlchemy
from app.models import *
from app.core.security_middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    IPWhitelistMiddleware,
    RequestLoggingMiddleware,
    RequestContextMiddleware,
    log_security_event
)
from app.routers import auth, courses, lessons, users, payments, payments_proxy, certificates, admin, dashboard, uploads, wishlist, instructor_reviews, quizzes, assignments, orders, blog, coupons, video, video_streaming, embed, youtube_embed, checkout, categories, tags, instructors, memberships, bundles, payouts
from app.routers import player, progress as progress_router, bunny, analytics, internships
from app.routers import lab_studio
from app.routers import admin_messages, candidate, companies, cohorts, company_billing, company_dashboard, student_workspace, export_import, ai, ai_tutor, ai_providers, question_banks, sileos, geogebra, three_d, virtual_labs, parents, course_type_capabilities
from app.routers import live_class_session, live_classes, live_class_attendance, live_class_polls
from app.routers import live_class_recordings, live_class_internal
from app.routers import notifications as notifications_router
from app.routers import superadmin
from app.routers import gradebook
from app.routers import h5p
from app.routers import games
from app.routers import gamification
from app.routers import hall_of_fame
from app.routers import certificate_designer
from app.routers import library
from app.api.v1 import certificate_verification
try:
    from app.routers import chunked_upload
    CHUNKED_UPLOAD_AVAILABLE = True
except ImportError as e:
    print(f"Chunked upload module not available: {e}")
    CHUNKED_UPLOAD_AVAILABLE = False

settings = get_settings()
from app.core.error_reporting import configure as configure_error_reporting
configure_error_reporting(settings)

# Build/release identity. RELEASE_TAG and DEPLOY_COLOR are injected by the
# blue-green deploy (see deploy/docker-compose.app.yml) so /health/version can
# tell you which image and which colour is actually serving traffic. They fall
# back to "unknown"/"none" for plain `docker-compose up` and local runs.
APP_VERSION = "1.0.0"
RELEASE_TAG = os.getenv("RELEASE_TAG", "unknown")
DEPLOY_COLOR = os.getenv("DEPLOY_COLOR", "none")

def _validate_live_class_secrets(environment: str) -> None:
    """Fail fast when Live Classes secrets are missing in production.

    JITSI_JWT_SECRET signs room-pinned Jitsi tokens (jitsi_token_service.py)
    and INTERNAL_TOKEN guards the recording-ingest endpoint
    (live_class_internal.py). Either being blank in production means those
    surfaces are either unusable or unguarded, so refuse to start rather than
    run degraded. Mirrors the VIDEO_SECRET fail-fast in routers/player.py,
    but as a startup check (not import-time) per the deviations file: dev
    and tests (ENVIRONMENT=development) must never trip this.
    """
    if environment != "production":
        return
    missing = []
    if len(settings.JITSI_JWT_SECRET or "") < 32:
        missing.append("JITSI_JWT_SECRET")
    if len(settings.INTERNAL_TOKEN or "") < 32:
        missing.append("INTERNAL_TOKEN")
    secret_values = {
        settings.SECRET_KEY,
        settings.JWT_SECRET,
        settings.JITSI_JWT_SECRET,
        settings.INTERNAL_TOKEN,
    }
    if len(secret_values) != 4:
        missing.append("distinct signing/internal secrets")
    if settings.CODE_RUNNER_TOKEN and (
        len(settings.CODE_RUNNER_TOKEN) < 32
        or settings.CODE_RUNNER_TOKEN in secret_values
    ):
        missing.append("independent 32+ character CODE_RUNNER_TOKEN")
    if missing:
        message = (
            "Live Classes misconfigured for production: "
            f"{', '.join(missing)} invalid. Set strong, unique values in "
            "deploy/.env.live before starting the backend "
            "(ENVIRONMENT=production)."
        )
        import logging
        logging.getLogger(__name__).critical(message)
        raise RuntimeError(message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    # Live Classes fail-fast (production only) — before init_db so a
    # misconfigured prod deploy never touches the database.
    _validate_live_class_secrets(settings.ENVIRONMENT)
    from app.workers.runtime import validate_api_mode
    validate_api_mode(settings)

    # Initialize database
    await init_db()

    # Initialize Redis
    await init_redis()

    # L-3 (Task 6 fix round): best-effort purge of stale certificate render
    # temp files (certificates_render_tmp/) left behind by a crash/kill
    # mid-render — see CertificateService.purge_stale_render_tmp docstring.
    try:
        from app.services.certificate_service import CertificateService
        CertificateService.purge_stale_render_tmp()
    except Exception:
        logging.getLogger(__name__).warning(
            "certificates_render_tmp startup purge failed", exc_info=True
        )

    background_tasks = []
    if settings.BACKGROUND_TASK_MODE == "inline":
        from app.services.reconciliation import reconciliation_loop
        from app.services.live_reminders import live_reminders_loop
        from app.services.campus_worker import campus_loop
        background_tasks = [asyncio.create_task(loop()) for loop in
                            (reconciliation_loop, live_reminders_loop, campus_loop)]

    print("SashaInfinity LMS Backend Started Successfully!")
    try:
        yield
    finally:
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)

    print("Shutting down SashaInfinity LMS Backend...")

# Create FastAPI application
app = FastAPI(
    title="SashaInfinity LMS API",
    description="Premium Learning Management System - Backend API",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
    # Fix redirect URLs to use HTTPS
    redirect_slashes=False
)

# A stable request id links browser, edge and backend diagnostics even when
# verbose request logging is disabled.
app.add_middleware(RequestContextMiddleware)
from app.core.runtime_telemetry import RuntimeTelemetryMiddleware
app.add_middleware(RuntimeTelemetryMiddleware)
from app.routers import observability
app.include_router(observability.router, prefix="/api/v1/internal/observability", tags=["Private metrics"])

# Security Middleware (order matters - IP Whitelist first)
if settings.ENABLE_IP_WHITELISTING or settings.BLOCKED_IP_RANGES:
    app.add_middleware(IPWhitelistMiddleware)

# Rate Limiting Middleware
if settings.ENABLE_API_RATE_LIMITING:
    app.add_middleware(RateLimitMiddleware)

# Request Logging Middleware (for security monitoring)
if settings.ENABLE_REQUEST_LOGGING:
    app.add_middleware(RequestLoggingMiddleware)

# CORS Middleware (centralized)
setup_cors(app)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Security Headers Middleware - DISABLED (handled by Nginx)
# app.add_middleware(SecurityHeadersMiddleware)

# Static Files - use relative paths based on backend directory
import pathlib
backend_dir = pathlib.Path(__file__).parent.parent
uploads_dir = backend_dir / "uploads"
certificates_dir = backend_dir / "certificates"

# Create directories if they don't exist
uploads_dir.mkdir(exist_ok=True)
certificates_dir.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# H5P asset serving (CORS) — review finding C1.
#
# The H5P player document (frontend/public/h5p-player.html) is loaded inside
# <iframe sandbox="allow-scripts"> WITHOUT allow-same-origin, which the
# browser treats as a unique OPAQUE origin ("null"). h5p-standalone does not
# fetch the package with plain <script>/<img> tags — it calls fetch() for
# h5p.json, content/content.json and the library JSON descriptors. A fetch()
# from an opaque origin is a CROSS-ORIGIN request whose Origin header is
# "null", so without an Access-Control-Allow-Origin response header the
# browser rejects the response and the player never boots — the whole H5P
# feature is dead on arrival. (Plain GETs for <script>/<link>/<img> are
# unaffected, which is why this was not caught by eyeballing the page.)
#
# These assets are already world-readable static files behind an unguessable
# 32-hex public_id, so ACAO:* grants no read access that a direct GET did not
# already have. Defence in depth on the response side:
#   * X-Content-Type-Options: nosniff — MIME sniffing off for package files
#   * Content-Security-Policy: sandbox — an asset opened as a TOP-LEVEL
#     document lands in a sandboxed browsing context, so uploaded HTML in a
#     package can never run script against this origin.
#
# Mounted BEFORE the general /uploads mount: Starlette matches mounts in
# registration order, so the /uploads/h5p subtree must be registered first to
# take precedence over /uploads.
# ---------------------------------------------------------------------------
import mimetypes as _mimetypes

from starlette.exceptions import HTTPException as StarletteHTTPException

# Windows' mimetypes registry has no entry for webfonts (verified on the
# deploy box: .woff/.woff2 both resolve to None), which would make
# StaticFiles fall back to a generic type for H5P library fonts. js/css/json/
# svg DO resolve correctly here, but they are asserted explicitly so a
# differently-configured host cannot silently regress them.
for _mt, _ext in (
    ("font/woff", ".woff"),
    ("font/woff2", ".woff2"),
    ("application/json", ".json"),
    ("text/javascript", ".js"),
    ("text/css", ".css"),
    ("image/svg+xml", ".svg"),
):
    _mimetypes.add_type(_mt, _ext)

h5p_uploads_dir = uploads_dir / "h5p"
h5p_uploads_dir.mkdir(exist_ok=True)


_H5P_ASSET_HEADERS = (
    (b"access-control-allow-origin", b"*"),
    (b"x-content-type-options", b"nosniff"),
    (b"content-security-policy", b"sandbox"),
)


class H5PAssetHeadersMiddleware:
    """Pure-ASGI middleware adding the CORS/hardening headers to every
    response from the H5P StaticFiles sub-app (including 404s and 304s)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                existing = {k.lower() for k, _ in headers}
                for name, value in _H5P_ASSET_HEADERS:
                    if name not in existing:
                        headers.append((name, value))
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except StarletteHTTPException as exc:
            # StaticFiles signals a missing/forbidden file by RAISING, which
            # would otherwise unwind past this middleware and be rendered by
            # the app-level exception handler — losing the CORS headers. A
            # header-less 4xx surfaces in the browser as an opaque CORS
            # failure instead of a clean 404, which makes a simple typo in a
            # package path very hard to diagnose. Render it here instead.
            response = PlainTextResponse(
                str(exc.detail), status_code=exc.status_code
            )
            for name, value in _H5P_ASSET_HEADERS:
                response.headers[name.decode()] = value.decode()
            await response(scope, receive, send)


app.mount(
    "/uploads/h5p",
    H5PAssetHeadersMiddleware(StaticFiles(directory=str(h5p_uploads_dir))),
    name="uploads-h5p",
)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
app.mount("/certificate-files", StaticFiles(directory=str(certificates_dir)), name="certificate-files")

# Placeholder Image Endpoints
@app.get("/api/placeholder/{width}/{height}")
async def get_placeholder_image(width: int, height: int):
    """Generate placeholder image"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"https://picsum.photos/{width}/{height}.jpg")

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Liveness probe. Answers "is this process up and serving HTTP?" and
    nothing more, so it stays cheap enough for Docker's HEALTHCHECK and the
    edge nginx to poll every few seconds. Use /health/ready for the deploy
    gate — a process can serve this while being unable to reach Postgres."""
    return {
        "status": "healthy",
        "service": "sashainfinity-lms-backend",
        "version": APP_VERSION,
        "release": RELEASE_TAG,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe used by the blue-green deploy to decide whether a newly
    started container may receive live traffic.

    Postgres is treated as required: without it every authenticated request
    fails, so a container that can't reach the DB must never be switched to.
    Redis is treated as degradable — RedisClient falls back to an in-process
    mock and the app keeps working with weaker rate limiting/caching, so a
    Redis outage reports `degraded` rather than blocking a deploy.

    Returns 200 when servable, 503 otherwise, so `curl -f` is a valid gate.
    """
    from sqlalchemy import text

    checks: dict[str, str] = {}
    degraded: list[str] = []

    # --- Postgres (required) ---
    db_ok = False
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
            db_ok = True
        finally:
            db.close()
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}: {exc}"

    # --- Redis (degradable) ---
    try:
        from app.core.redis import RedisClient
        client = await RedisClient.get_instance()
        await client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}: {exc}"
        degraded.append("redis")

    ready = db_ok
    payload = {
        "status": "healthy" if ready else "unhealthy",
        "ready": ready,
        "service": "sashainfinity-lms-backend",
        "version": APP_VERSION,
        "release": RELEASE_TAG,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }
    if degraded:
        payload["degraded"] = degraded

    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.get("/health/version", include_in_schema=False)
async def version_info():
    """Which build is actually serving. The deploy script reads this after the
    traffic switch to confirm the edge is pointing at the new release rather
    than at a stale container that happened to stay healthy."""
    return {
        "version": APP_VERSION,
        "release": RELEASE_TAG,
        "color": DEPLOY_COLOR,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """No-op favicon so browsers/headless Chrome requesting /favicon.ico on the
    backend origin get a clean 204 instead of the generic
    {"detail":"Endpoint not found"} 404 (which looks alarming in DevTools)."""
    from fastapi import Response
    return Response(status_code=204)


# Edgyy Hosted Payment Page
@app.get("/pay", response_class=HTMLResponse)
async def hosted_payment_page(session_id: str, db: Session = Depends(get_db)):
    """
    Hosted payment page for Edgyy sessions.

    Renders a page with Razorpay checkout.js. User completes payment here,
    then gets redirected back to Edgyy's return_url.
    """
    from app.models.edgyy_payment import EdgyyPaymentSession, EdgyyPaymentSessionStatus

    session = db.query(EdgyyPaymentSession).filter(
        EdgyyPaymentSession.session_id == session_id
    ).first()

    if not session:
        return HTMLResponse(
            content="<html><body><h1>Invalid Session</h1><p>This payment session does not exist.</p></body></html>",
            status_code=404,
        )

    if session.status != EdgyyPaymentSessionStatus.PENDING:
        return HTMLResponse(
            content=f"<html><body><h1>Session {session.status}</h1><p>This payment session is no longer valid.</p></body></html>",
            status_code=400,
        )

    # Check expiry
    if session.expires_at and session.expires_at < datetime.now(timezone.utc):
        session.status = EdgyyPaymentSessionStatus.EXPIRED
        db.commit()
        return HTMLResponse(
            content="<html><body><h1>Session Expired</h1><p>This payment session has expired. Please start a new payment.</p></body></html>",
            status_code=400,
        )

    # Get Razorpay key
    key_id = settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Complete Payment - Sasha Infinity</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{ font-size: 24px; color: #333; margin-bottom: 10px; }}
        .amount {{ font-size: 36px; font-weight: bold; color: #667eea; margin: 20px 0; }}
        .description {{ color: #666; margin-bottom: 30px; }}
        .pay-btn {{
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        .pay-btn:hover {{ transform: scale(1.02); }}
        .secure {{ text-align: center; margin-top: 20px; color: #999; font-size: 14px; }}
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
            display: none;
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .success {{ display: none; text-align: center; }}
        .success svg {{ width: 64px; height: 64px; color: #10b981; }}
    </style>
</head>
<body>
    <div class="container">
        <div id="payment-form">
            <h1>Complete Payment</h1>
            <p class="description">Secure payment powered by Razorpay</p>
            <div class="amount">₹{float(session.amount):.2f}</div>
            <button class="pay-btn" id="pay-btn">Pay Now</button>
            <div class="secure">🔒 Secured by Razorpay</div>
        </div>
        <div class="spinner" id="spinner"></div>
        <div class="success" id="success">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <h2>Payment Successful!</h2>
            <p>Redirecting...</p>
        </div>
    </div>

    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
        const sessionId = '{session_id}';
        const orderId = '{session.razorpay_order_id}';
        const keyId = '{key_id}';
        const amount = {int(float(session.amount) * 100)};
        const currency = '{session.currency}';
        const name = 'Sasha Infinity';
        const description = 'Edgyy Payment';
        const returnUrl = '{session.return_url}';
        const registrationId = '{session.edgyy_registration_id}';

        document.getElementById('pay-btn').addEventListener('click', function(e) {{
            e.preventDefault();
            document.getElementById('payment-form').style.display = 'none';
            document.getElementById('spinner').style.display = 'block';

            const options = {{
                key: keyId,
                amount: amount,
                currency: currency,
                name: name,
                description: description,
                order_id: orderId,
                handler: function(response) {{
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('success').style.display = 'block';

                    // Call internal verify endpoint
                    fetch('/api/v1/payments/proxy/internal/verify-session', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            session_id: sessionId
                        }})
                    }})
                    .then(res => res.json())
                    .then(data => {{
                        if (data.redirect_url) {{
                            window.location.href = data.redirect_url;
                        }} else {{
                            window.location.href = returnUrl + (returnUrl.includes('?') ? '&' : '?') + 'status=error&session_id=' + sessionId;
                        }}
                    }})
                    .catch(err => {{
                        console.error('Verify error:', err);
                        window.location.href = returnUrl + (returnUrl.includes('?') ? '&' : '?') + 'status=error&session_id=' + sessionId;
                    }});
                }},
                modal: {{
                    ondismiss: function() {{
                        // Call failed endpoint
                        fetch('/api/v1/payments/proxy/internal/session-failed', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                session_id: sessionId,
                                error: 'User cancelled payment'
                            }})
                        }})
                        .then(res => res.json())
                        .then(data => {{
                            window.location.href = data.redirect_url || returnUrl;
                        }})
                        .catch(err => {{
                            window.location.href = returnUrl + (returnUrl.includes('?') ? '&' : '?') + 'status=cancelled&session_id=' + sessionId;
                        }});
                    }}
                }},
                theme: {{
                    color: '#667eea'
                }}
            }};

            const rzp = new Razorpay(options);
            rzp.open();
        }});

        // Auto-open checkout on page load
        setTimeout(function() {{
            document.getElementById('pay-btn').click();
        }}, 500);
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html_content)


# ---------------------------------------------------------------------------
# SEO infrastructure — robots.txt, sitemap.xml, and crawlable blog HTML.
#
# The SPA renders every page client-side, so search engines never see article
# content. nginx diverts crawler user-agents to /_prerender (see
# nginx/conf.d/default.conf), which used to answer with an OG-tag stub plus a
# self-referencing redirect — an unindexable soft 404 (SEO audit, 2026-08-21).
# The helpers below give blog routes real server-rendered HTML; every other
# route keeps the stub so social-link previews are unchanged.
# ---------------------------------------------------------------------------

SITE_URL = "https://sashainfinity.com"
SITE_NAME = "SashaInfinity"
DEFAULT_OG_IMAGE = "https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png"

_TAG_RE = re.compile(r"<[^>]+>")


def _seo_iso_date(dt):
    """Format a (naive-UTC) model datetime as ISO 8601 with a Z suffix."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def _absolute_media_url(url):
    """Crawlers reject relative image paths; absolute URLs pass through."""
    if not url:
        return url
    if url.startswith("http"):
        return url
    return f"{SITE_URL}{url if url.startswith('/') else '/' + url}"


def optimize_cloudinary_url(url: str) -> str:
    """Shrink an OG image to a WhatsApp/Facebook-friendly thumbnail.

    WhatsApp/Facebook silently drop link-preview images over ~1MB, and our
    course-thumbnails / uploads are multi-MB PNGs — so title/desc show but no
    thumbnail. Shrink to a compact JPEG (~1200x630) so the preview image
    actually renders.
    """
    if not url:
        return url
    # Cloudinary: use its native transform pipeline.
    if 'cloudinary.com' in url and '/upload/' in url:
        parts = url.split('/upload/')
        if len(parts) == 2:
            return f"{parts[0]}/upload/f_jpg,q_80,w_1200/{parts[1]}"
        return url
    # Everything else (local PNGs, remote images) → resize/compress via a
    # proxy so large source images become a WhatsApp-friendly thumbnail.
    if url.startswith('http') and 'images.weserv.nl' not in url:
        from urllib.parse import quote
        stripped = url.split('://', 1)[-1]
        return f"https://images.weserv.nl/?url={quote(stripped)}&w=1200&h=630&fit=cover&output=jpg&q=80"
    return url


def _plain_text_excerpt(content_html, excerpt, limit=200):
    """Build a plain-text meta description from the excerpt or the body HTML."""
    text = (excerpt or "").strip()
    if not text and content_html:
        text = _TAG_RE.sub(" ", content_html)
    return " ".join(text.split())[:limit].rstrip()


def _get_published_blog_post(slug):
    """Fetch a PUBLISHED post by slug as a plain dict, or None.

    Values are extracted while the session is open so nothing lazy-loads
    after the session closes.
    """
    db = SessionLocal()
    try:
        post = (
            db.query(BlogPost)
            .filter(BlogPost.slug == slug, BlogPost.status == "PUBLISHED")
            .first()
        )
        if post is None:
            return None
        author_name = None
        try:
            if post.author is not None:
                author_name = post.author.display_name
        except Exception:
            author_name = None
        return {
            "title": post.title,
            "slug": post.slug,
            "content": post.content,
            "excerpt": post.excerpt,
            "featured_image": post.featured_image,
            "category": post.category,
            "post_date": post.post_date or post.created_at,
            "post_modified": post.post_modified or post.updated_at,
            "meta_title": post.meta_title,
            "meta_description": post.meta_description,
            "author_name": author_name or "SashaInfinity Team",
        }
    except Exception as e:
        print(f"[SEO] Blog post lookup failed for '{slug}': {e}")
        return None
    finally:
        db.close()


def _get_published_blog_posts(limit=1000):
    """List PUBLISHED posts (newest first) as plain dicts."""
    db = SessionLocal()
    try:
        posts = (
            db.query(BlogPost)
            .filter(BlogPost.status == "PUBLISHED")
            .order_by(BlogPost.post_date.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "slug": p.slug,
                "title": p.title,
                "excerpt": p.excerpt,
                "post_date": p.post_date or p.created_at,
                "post_modified": p.post_modified or p.updated_at,
            }
            for p in posts
        ]
    except Exception as e:
        print(f"[SEO] Blog listing query failed: {e}")
        return []
    finally:
        db.close()


def _get_related_blog_posts(slug, category=None, limit=3):
    """Same-category posts first, recent posts as fallback."""
    db = SessionLocal()
    try:
        base = db.query(BlogPost).filter(
            BlogPost.status == "PUBLISHED", BlogPost.slug != slug
        )
        posts = []
        if category:
            posts = (
                base.filter(BlogPost.category == category)
                .order_by(BlogPost.post_date.desc())
                .limit(limit)
                .all()
            )
        if len(posts) < limit:
            skip = [slug] + [p.slug for p in posts]
            recent = (
                base.filter(~BlogPost.slug.in_(skip))
                .order_by(BlogPost.post_date.desc())
                .limit(limit - len(posts))
                .all()
            )
            posts = list(posts) + list(recent)
        return [{"slug": p.slug, "title": p.title} for p in posts]
    except Exception as e:
        print(f"[SEO] Related posts query failed: {e}")
        return []
    finally:
        db.close()


_SEO_PAGE_STYLE = """
    body { font-family: -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
           margin: 0; color: #1a202c; background: #ffffff; line-height: 1.65; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 24px 16px 48px; }
    .site-header { border-bottom: 1px solid #e2e8f0; }
    .site-header a { display: block; max-width: 720px; margin: 0 auto;
                     padding: 14px 16px; font-weight: 700; color: #1a202c;
                     text-decoration: none; }
    h1 { font-size: 1.9em; line-height: 1.25; margin: 0.6em 0 0.3em; }
    .byline { color: #64748b; font-size: 0.9em; margin: 0 0 1.5em; }
    .post-content img { max-width: 100%; height: auto; }
    .post-content a { word-break: break-word; }
    .post-card { margin: 0 0 1.8em; }
    .post-card h2 { margin: 0 0 0.2em; font-size: 1.25em; }
    .post-card a { color: #1a4fd8; }
    .meta { color: #64748b; font-size: 0.85em; margin: 0 0 0.4em; }
    .related { border-top: 1px solid #e2e8f0; margin-top: 2.5em; padding-top: 1em; }
    .related ul { padding-left: 1.2em; }
    .backlink { margin-top: 2em; }
    .backlink a { color: #1a4fd8; }
"""


def _blog_post_response(post):
    """Full crawlable HTML for a single blog post — what Google actually reads."""
    from fastapi.responses import Response

    title = post["meta_title"] or post["title"]
    description = _plain_text_excerpt(
        post["content"], post["meta_description"] or post["excerpt"]
    )
    url = f"{SITE_URL}/blog/{post['slug']}"
    image = optimize_cloudinary_url(_absolute_media_url(post["featured_image"])) or DEFAULT_OG_IMAGE
    published = _seo_iso_date(post["post_date"])
    modified = _seo_iso_date(post["post_modified"]) or published

    json_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": description,
        "image": [image],
        "datePublished": published,
        "dateModified": modified,
        "author": {"@type": "Person", "name": post["author_name"]},
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "logo": {"@type": "ImageObject", "url": DEFAULT_OG_IMAGE},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }
    json_ld = json.dumps({k: v for k, v in json_ld.items() if v is not None}, ensure_ascii=False)

    breadcrumbs = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
                {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE_URL}/blog"},
                {"@type": "ListItem", "position": 3, "name": title},
            ],
        },
        ensure_ascii=False,
    )

    related = _get_related_blog_posts(post["slug"], post.get("category"))
    related_html = ""
    if related:
        items = "".join(
            f'<li><a href="/blog/{escape(r["slug"])}">{escape(r["title"])}</a></li>'
            for r in related
        )
        related_html = (
            f'<section class="related"><h2>Related posts</h2><ul>{items}</ul></section>'
        )

    pd = post["post_date"]
    date_label = f"{pd:%B} {pd.day}, {pd.year}" if pd else ""
    byline = f"By {escape(post['author_name'])}"
    if date_label:
        byline += f" · {date_label}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}">
    <link rel="canonical" href="{escape(url)}">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{escape(url)}">
    <meta property="og:title" content="{escape(title)}">
    <meta property="og:description" content="{escape(description)}">
    <meta property="og:image" content="{escape(image)}">
    <meta property="og:site_name" content="{SITE_NAME} LMS">"""

    if published:
        html += f"""
    <meta property="article:published_time" content="{published}">
    <meta property="article:modified_time" content="{modified or published}">"""

    html += f"""

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{escape(url)}">
    <meta name="twitter:title" content="{escape(title)}">
    <meta name="twitter:description" content="{escape(description)}">
    <meta name="twitter:image" content="{escape(image)}">

    <!-- Structured data -->
    <script type="application/ld+json">{json_ld}</script>
    <script type="application/ld+json">{breadcrumbs}</script>

    <style>{_SEO_PAGE_STYLE}</style>
</head>
<body>
    <header class="site-header"><a href="/">{SITE_NAME}</a></header>
    <div class="wrap">
        <article>
            <h1>{escape(post['title'])}</h1>
            <p class="byline">{byline}</p>
            <div class="post-content">
{post["content"]}
            </div>
        </article>
        {related_html}
        <p class="backlink"><a href="/blog">&larr; More from the {SITE_NAME} blog</a></p>
    </div>
</body>
</html>"""

    return Response(
        content=html,
        status_code=200,
        media_type="text/html",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _blog_listing_response():
    """Crawlable blog listing: every published post linked with a real anchor."""
    from fastapi.responses import Response

    posts = _get_published_blog_posts()
    cards = []
    for p in posts:
        pd = p["post_date"]
        date_label = f"{pd:%B} {pd.day}, {pd.year}" if pd else ""
        excerpt = _plain_text_excerpt(None, p["excerpt"], 160)
        card = (
            f'<article class="post-card">'
            f'<h2><a href="/blog/{escape(p["slug"])}">{escape(p["title"])}</a></h2>'
        )
        if date_label:
            card += f'<p class="meta">{date_label}</p>'
        if excerpt:
            card += f"<p>{escape(excerpt)}</p>"
        card += "</article>"
        cards.append(card)

    description = f"Expert-led articles on technology, courses, and careers from the {SITE_NAME} team."
    url = f"{SITE_URL}/blog"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog | {SITE_NAME}</title>
    <meta name="description" content="{escape(description)}">
    <link rel="canonical" href="{url}">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="Blog | {SITE_NAME}">
    <meta property="og:description" content="{escape(description)}">
    <meta property="og:image" content="{DEFAULT_OG_IMAGE}">
    <meta property="og:site_name" content="{SITE_NAME} LMS">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{url}">
    <meta name="twitter:title" content="Blog | {SITE_NAME}">
    <meta name="twitter:description" content="{escape(description)}">
    <meta name="twitter:image" content="{DEFAULT_OG_IMAGE}">

    <style>{_SEO_PAGE_STYLE}</style>
</head>
<body>
    <header class="site-header"><a href="/">{SITE_NAME}</a></header>
    <div class="wrap">
        <h1>{SITE_NAME} Blog</h1>
        {''.join(cards) if cards else '<p>No posts published yet.</p>'}
    </div>
</body>
</html>"""

    return Response(
        content=html,
        status_code=200,
        media_type="text/html",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/robots.txt")
async def robots_txt():
    """Plain-text robots.txt so the SPA fallback cannot answer it with HTML."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return PlainTextResponse(content=content, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/sitemap.xml")
async def sitemap_xml():
    """Sitemap generated from PUBLISHED blog posts plus the key static pages."""
    from fastapi.responses import Response

    entries = "".join(
        f"<url><loc>{escape(u)}</loc></url>"
        for u in (f"{SITE_URL}/", f"{SITE_URL}/blog", f"{SITE_URL}/courses", f"{SITE_URL}/internships")
    )
    for p in _get_published_blog_posts():
        lastmod = _seo_iso_date(p["post_modified"])
        lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        loc = escape(f"{SITE_URL}/blog/{p['slug']}")
        entries += f"<url><loc>{loc}</loc>{lm}</url>"

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# Prerender Endpoint - for social media crawler support
@app.get("/_prerender/{path:path}")
async def prerender_proxy(path: str, request: Request):
    """
    Generate HTML with server-side OG meta tags for social media crawlers.
    """
    import re

    user_agent = request.headers.get('user-agent', '')

    # Verify this is actually a crawler
    crawlers = ['twitterbot', 'facebookexternalhit', 'linkedinbot', 'slackbot',
                'telegrambot', 'whatsapp', 'googlebot', 'bingbot', 'slurp',
                'duckduckbot', 'baiduspider', 'yandexbot', 'pinterest', 'vkshare']

    is_crawler = any(crawler in user_agent.lower() for crawler in crawlers)

    if not is_crawler:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"/{path}")

    # Blog routes serve full crawlable HTML so search engines can index them
    # (SEO audit 2026-08-21, Findings 1 & 2). All other routes keep the
    # OG-tag stub below, which social-preview crawlers rely on.
    if path.rstrip('/') == 'blog':
        return _blog_listing_response()
    blog_slug_match = re.match(r'blog/([^/]+)', path)
    if blog_slug_match:
        post = _get_published_blog_post(blog_slug_match.group(1))
        if post is not None:
            return _blog_post_response(post)
        # Unknown or unpublished slug: fall through to the generic stub below

    # Fetch metadata for OG tags
    og_title = "SashaInfinity - Premium Technology Learning Platform"
    og_description = "Master cutting-edge technologies with expert-led courses"
    og_image = "https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png"
    og_type = "website"
    og_url = f"https://sashainfinity.com/{path}"

    # Check if this is a course
    course_match = re.match(r'courses/([^/]+)', path)
    if course_match:
        try:
            course_slug = course_match.group(1)
            from httpx import AsyncClient
            async with AsyncClient(timeout=10.0) as api_client:
                course_response = await api_client.get(
                    f"http://localhost:8000/api/v1/courses/{course_slug}"
                )
                if course_response.status_code == 200:
                    course_data = course_response.json()
                    og_title = course_data.get('title', og_title)
                    og_description = (course_data.get('excerpt') or course_data.get('description', '') or og_description)[:200]
                    og_image = (
                        course_data.get('thumbnail') or
                        course_data.get('course_thumbnail') or
                        course_data.get('featured_image') or
                        og_image
                    )
                    print(f"[Prerender] Course: {og_title} | Image: {og_image}")
        except Exception as e:
            print(f"[Prerender] Course fetch error: {e}")

    # Check if this is a public instructor profile (/instructor/{id})
    instructor_match = re.match(r'instructor/([^/]+)', path)
    if instructor_match:
        try:
            instructor_id = instructor_match.group(1)
            from httpx import AsyncClient
            async with AsyncClient(timeout=10.0) as api_client:
                instructor_response = await api_client.get(
                    f"http://localhost:8000/api/v1/users/instructors/{instructor_id}"
                )
                if instructor_response.status_code == 200:
                    ins = instructor_response.json()
                    ins_name = ins.get('name') or ins.get('display_name') or 'Instructor'
                    og_title = f"{ins_name} | Instructor at SashaInfinity"
                    bio_text = (ins.get('bio') or ins.get('description') or ins.get('expertise') or '')
                    og_description = (bio_text.strip() or f"Learn from {ins_name} on SashaInfinity LMS.")[:200].replace('<', '').replace('>', '')
                    photo = ins.get('profile_photo') or ins.get('avatar') or ''
                    if photo:
                        og_image = photo
                    og_type = "profile"
                    print(f"[Prerender] Instructor: {og_title} | Image: {og_image}")
        except Exception as e:
            print(f"[Prerender] Instructor fetch error: {e}")

    # Check if this is an internship
    internship_match = re.match(r'internships/([^/]+)', path)
    if internship_match:
        try:
            internship_slug = internship_match.group(1)
            from httpx import AsyncClient
            async with AsyncClient(timeout=10.0) as api_client:
                internship_response = await api_client.get(
                    f"http://localhost:8000/api/v1/internships/{internship_slug}"
                )
                if internship_response.status_code == 200:
                    internship_data = internship_response.json()
                    og_title = internship_data.get('title', og_title)
                    og_description = (internship_data.get('description') or '')[:200].replace('<', '').replace('>', '')
                    og_image = internship_data.get('cover_image', og_image)
                    print(f"[Prerender] Internship: {og_title} | Image: {og_image}")
        except Exception as e:
            print(f"[Prerender] Internship fetch error: {e}")

    # Check if this is a user profile
    user_match = re.match(r'u/([^/]+)', path)
    if user_match:
        try:
            username = user_match.group(1)
            from httpx import AsyncClient
            async with AsyncClient(timeout=10.0) as api_client:
                user_response = await api_client.get(
                    f"http://localhost:8000/api/v1/users/public/{username}"
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    og_title = f"{user_data.get('display_name', username)}'s Profile | SashaInfinity"
                    bio_text = user_data.get('bio') or ''
                    og_description = bio_text if bio_text.strip() else f"Check out {user_data.get('display_name', username)}'s public profile on SashaInfinity LMS."
                    og_description = og_description[:200].replace('<', '').replace('>', '')
                    profile_photo = user_data.get('profile_photo', '')
                    if profile_photo:
                        if not profile_photo.startswith('http'):
                            og_image = f"https://sashainfinity.com{profile_photo if profile_photo.startswith('/') else '/' + profile_photo}"
                        else:
                            og_image = profile_photo
                    else:
                        og_image = "https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png"
                    print(f"[Prerender] User Profile: {og_title} | Image: {og_image}")
        except Exception as e:
            print(f"[Prerender] User Profile fetch error: {e}")

    # Crawlers reject relative image paths — force an absolute URL for every
    # branch (course/blog/internship return relative thumbnails). Handles both
    # `/path` and `path`, and leaves already-absolute (http) URLs untouched.
    if og_image and not og_image.startswith('http'):
        og_image = f"https://sashainfinity.com{og_image if og_image.startswith('/') else '/' + og_image}"

    og_image = optimize_cloudinary_url(og_image)

    # Generate HTML with correct OG tags
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{og_title}</title>
    <meta name="description" content="{og_description}">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="{og_type}">
    <meta property="og:url" content="{og_url}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:site_name" content="SashaInfinity LMS">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{og_url}">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{og_description}">
    <meta name="twitter:image" content="{og_image}">

    <script>window.location.href = "/{path}";</script>
    <noscript><meta http-equiv="refresh" content="0;url=/{path}"></noscript>
</head>
<body>
    <p>Redirecting to <a href="/{path}">{og_title}</a>...</p>
</body>
</html>"""

    from fastapi.responses import Response
    return Response(
        content=html,
        status_code=200,
        media_type='text/html',
        headers={
            'Cache-Control': 'public, max-age=3600',
        }
    )

# Image Thumbnail Endpoint for Social Media
@app.get("/_thumb/{path:path}")
async def get_thumbnail(path: str, request: Request):
    """
    Serve thumbnail version of images for social media sharing.
    Redirects large images to default logo, serves smaller images directly.
    """
    from fastapi.responses import RedirectResponse
    import os

    # For now, use default logo for all images since local images are too large
    # TODO: Implement image resizing with Pillow
    return RedirectResponse(
        url="https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png",
        status_code=302
    )

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SashaInfinity LMS Backend API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "platform": "SashaInfinity"
    }

# Exception Handlers
# Fields that must never reach logs — validation failures on /auth/login,
# /auth/register etc. carry plaintext credentials in the rejected body.
_REDACTED_BODY_FIELDS = {"password", "confirm_password", "otp_code", "refresh_token", "access_token"}

def _redact_body(body) -> str:
    import json as _json
    if isinstance(body, dict):
        parsed = dict(body)
        for field in _REDACTED_BODY_FIELDS:
            if field in parsed:
                parsed[field] = "***REDACTED***"
        return _json.dumps(parsed)
    raw = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    try:
        parsed = _json.loads(raw)
        if isinstance(parsed, dict):
            for field in _REDACTED_BODY_FIELDS:
                if field in parsed:
                    parsed[field] = "***REDACTED***"
            return _json.dumps(parsed)
    except Exception:
        pass
    # Not JSON — mask conservatively by blanking any redacted field substring.
    import re as _re
    for field in _REDACTED_BODY_FIELDS:
        raw = _re.sub(rf"(\"{field}\"\s*:\s*\")[^\"]*(\")", r"\1***REDACTED***\2", raw)
        raw = _re.sub(rf"('{field}'\s*:\s*')[^']*(')", r"\1***REDACTED***\2", raw)
    return raw

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Strip 'input' echoes (and ctx errors embedding them) so a failing
    # credential field can never reach the logs via the errors list either.
    _safe_errors = [
        {k: v for k, v in err.items() if k not in ("input", "ctx")}
        for err in exc.errors()
    ]
    print(f"Validation error on {request.url}: {_safe_errors}")
    try:
        body_str = _redact_body(exc.body)
        print(f"Request body: {body_str}")
    except Exception as e:
        print(f"Could not decode request body: {e}")
        body_str = "Unable to decode request body"

    # Format error messages in a user-friendly way
    errors = exc.errors()
    formatted_errors = []
    for error in errors:
        field = error.get('loc', [])[-1] if error.get('loc') else 'unknown'
        msg = error.get('msg', 'Validation error')
        # Extract the actual error message from Pydantic's value_error
        if 'ctx' in error and 'error' in error['ctx']:
            msg = str(error['ctx']['error'])
        formatted_errors.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=422,
        content={"detail": " | ".join(formatted_errors) if formatted_errors else "Validation error"}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    print(f"ValueError on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include Routers with /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(course_type_capabilities.router, prefix="/api/v1", tags=["Course Types"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(tags.router, prefix="/api/v1/tags", tags=["Tags"])
app.include_router(instructors.router, prefix="/api/v1/instructors", tags=["Instructors"])
app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["Lessons"])
app.include_router(checkout.router, prefix="/api/v1/checkout", tags=["Checkout"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(payments_proxy.router, prefix="/api/v1/payments", tags=["Payments Proxy"])
app.include_router(memberships.router, prefix="/api/v1/memberships", tags=["Memberships"])
app.include_router(bundles.router, prefix="/api/v1/bundles", tags=["Bundles"])
app.include_router(library.router, prefix="/api/v1/library", tags=["Library"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(certificates.router, prefix="/api/v1/certificates", tags=["Certificates"])
app.include_router(certificate_designer.router, prefix="/api/v1/certificates/designer", tags=["Certificate Designer"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(superadmin.router, prefix="/api/v1/superadmin", tags=["SuperAdmin"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(
    payouts.instructor_router,
    prefix="/api/v1/instructor/withdrawals",
    tags=["Payouts"],
)
app.include_router(
    payouts.admin_router,
    prefix="/api/v1/admin/withdrawals",
    tags=["Payouts"],
)
app.include_router(uploads.router, prefix="/api/v1/upload", tags=["Uploads"])
app.include_router(wishlist.router, prefix="/api/v1/wishlist", tags=["Wishlist"])
app.include_router(instructor_reviews.router, prefix="/api/v1/instructor-reviews", tags=["Instructor Reviews"])
app.include_router(quizzes.router, prefix="/api/v1", tags=["Quizzes"])
app.include_router(assignments.router, prefix="/api/v1", tags=["Assignments"])
app.include_router(gradebook.router, prefix="/api/v1", tags=["Gradebook"])
app.include_router(h5p.router, prefix="/api/v1/h5p", tags=["H5P"])
app.include_router(games.router, prefix="/api/v1/games", tags=["Games"])
app.include_router(gamification.router, prefix="/api/v1/gamification", tags=["Gamification"])
app.include_router(certificate_verification.router, prefix="/api/v1", tags=["Certificate Verification"])
app.include_router(blog.router, prefix="/api/v1/blog", tags=["Blog"])
app.include_router(hall_of_fame.router, prefix="/api/v1/hall-of-fame", tags=["HallOfFame"])
app.include_router(coupons.router, prefix="/api/v1/coupons", tags=["Coupons"])
app.include_router(video.router, prefix="/api/v1/extract", tags=["Video Extraction"])
app.include_router(video_streaming.router, prefix="/api/v1/stream", tags=["Video Streaming"])
app.include_router(embed.router, prefix="/api/v1/embed", tags=["Video Embed"])
app.include_router(youtube_embed.router, prefix="/api/v1/youtube", tags=["YouTube Embed"])
app.include_router(player.router, prefix="/api/v1/video", tags=["Player"])
app.include_router(progress_router.router, prefix="/api/v1/progress", tags=["Progress"])
app.include_router(bunny.router, prefix="/api/v1/bunny", tags=["Bunny"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(internships.router, prefix="/api/v1", tags=["Internships"])
app.include_router(candidate.router, prefix="/api/v1/candidates", tags=["Candidate Profile"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(company_dashboard.router, prefix="/api/v1/companies", tags=["Company Dashboard"])
app.include_router(company_billing.router, prefix="/api/v1/companies/billing", tags=["Company Billing"])
app.include_router(cohorts.router, prefix="/api/v1/cohorts", tags=["Cohorts"])
app.include_router(student_workspace.router, prefix="/api/v1/student", tags=["Student Workspace"])
app.include_router(admin_messages.router, prefix="/api/v1/admin/messages", tags=["Admin Messages"])
app.include_router(export_import.router, prefix="/api/v1", tags=["Export-Import"])
# --- SILEOS feature pack (docs/SILEOS_FEATURES.md) ---
app.include_router(question_banks.router, prefix="/api/v1/question-banks", tags=["SILEOS Question Banks"])
app.include_router(sileos.router, prefix="/api/v1", tags=["SILEOS Pack"])
app.include_router(ai.router, prefix="/api/v1", tags=["SILEOS AI"])
app.include_router(ai_tutor.router, prefix="/api/v1/ai", tags=["AI Teaching Layer"])
app.include_router(ai_providers.router, prefix="/api/v1/ai", tags=["AI Provider Vault"])
app.include_router(parents.router, prefix="/api/v1/parents", tags=["Parents"])
from app.routers import parent_portal
app.include_router(parent_portal.router, prefix="/api/v1/parents", tags=["Parent portal"])
app.include_router(geogebra.router, prefix="/api/v1/geogebra", tags=["GeoGebra"])
app.include_router(three_d.router, prefix="/api/v1/three-d", tags=["3D Models"])
app.include_router(virtual_labs.router, prefix="/api/v1/virtual-labs", tags=["Virtual Labs"])
app.include_router(lab_studio.router, prefix="/api/v1/lab-studio", tags=["Lab Studio"])
from app.routers import content_library_admin  # noqa: E402
from app.routers import scorable_items  # noqa: E402
app.include_router(scorable_items.router, prefix="/api/v1/scorable-items", tags=["Scorable Items"])
from app.routers import three_d_tasks  # noqa: E402
app.include_router(three_d_tasks.router, prefix="/api/v1/three-d-tasks", tags=["3D Tasks"])
from app.routers import mastery  # noqa: E402
app.include_router(mastery.router, prefix="/api/v1/mastery", tags=["Mastery Graph"])
from app.routers import tag_taxonomy  # noqa: E402
app.include_router(tag_taxonomy.router, prefix="/api/v1/tag-taxonomy", tags=["Tag Taxonomy"])
from app.routers import studio  # noqa: E402
from app.routers import ai_engines  # noqa: E402
app.include_router(ai_engines.router, prefix="/api/v1/ai", tags=["AI Teaching Layer"])
from app.routers import flywheel  # noqa: E402
app.include_router(flywheel.router, prefix="/api/v1/flywheel", tags=["Flywheel"])
from app.routers import funnel  # noqa: E402
app.include_router(funnel.router, prefix="/api/v1/funnel", tags=["Funnel"])
from app.routers import course_ops  # noqa: E402
app.include_router(course_ops.router, prefix="/api/v1/course-ops", tags=["Course Ops"])
from app.routers import learning_signals  # noqa: E402
app.include_router(learning_signals.router, prefix="/api/v1/signals", tags=["Learning Signals"])
from app.routers import learning_planner  # noqa: E402
app.include_router(learning_planner.router, prefix="/api/v1/planner", tags=["Learning Planner"])
app.include_router(studio.router, prefix="/api/v1/studio", tags=["Studio"])
app.include_router(content_library_admin.router, prefix="/api/v1/admin/content-library", tags=["Admin Content Libraries"])
app.include_router(live_class_session.router, prefix="/api/v1/live", tags=["Live Classes"])
app.include_router(live_classes.router, prefix="/api/v1/live", tags=["Live Classes"])
app.include_router(live_class_attendance.router, prefix="/api/v1/live", tags=["Live Classes"])
app.include_router(live_class_polls.router, prefix="/api/v1/live", tags=["Live Classes"])
app.include_router(live_class_recordings.router, prefix="/api/v1/live", tags=["Live Classes"])
app.include_router(live_class_internal.router, prefix="/api/v1/internal/live", tags=["Live Classes Internal"])

# Include chunked upload router if available
if CHUNKED_UPLOAD_AVAILABLE:
    app.include_router(chunked_upload.router, prefix="/api/v1/upload/chunked", tags=["Chunked Uploads"])
    print("Chunked upload endpoints enabled")
else:
    print("Chunked upload endpoints disabled - using regular uploads only")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info"
    )

from app.routers import assessment_studio  # noqa: E402
app.include_router(assessment_studio.router, prefix="/api/v1/assessment-studio", tags=["Assessment Studio"])

from app.routers import recording_lessons  # noqa: E402
app.include_router(recording_lessons.router, prefix="/api/v1/recording-lessons", tags=["Recording Lessons"])

from app.routers import operations  # noqa: E402
app.include_router(operations.router, prefix="/api/v1/admin/operations", tags=["Admin Operations"])

from app.routers import course_packages  # noqa: E402
app.include_router(course_packages.router, prefix="/api/v1/course-packages", tags=["Course Packages"])

from app.routers import exam_papers
app.include_router(exam_papers.router, prefix="/api/v1/exam-papers", tags=["Exam Papers"])
from app.routers import institutions
app.include_router(institutions.router, prefix="/api/v1/institutions", tags=["Institutions"])

from app.routers import platform_tenants
app.include_router(
    platform_tenants.router,
    prefix="/api/v1/platform/tenants",
    tags=["Platform tenant control plane"],
)

from app.routers import commercial
app.include_router(
    commercial.router,
    prefix="/api/v1/platform/commercial",
    tags=["Platform commercial control plane"],
)

from app.routers import coding_assessments, coding_judge_internal
app.include_router(
    coding_assessments.router,
    prefix="/api/v1/utporul/coding",
    tags=["Utporul coding assessments"],
)
app.include_router(
    coding_judge_internal.router,
    prefix="/api/v1/internal/coding",
    tags=["Internal code judge"],
)

from app.routers import meiporul_operations
app.include_router(
    meiporul_operations.router,
    prefix="/api/v1/meiporul/operations",
    tags=["Meiporul field operations"],
)

from app.routers import campus_growth
app.include_router(campus_growth.router, prefix="/api/v1/campus-growth", tags=["Campus growth"])

from app.routers import campus_operations, campus_billing
app.include_router(campus_operations.router, prefix="/api/v1/institutions", tags=["Campus operations"])
app.include_router(campus_billing.router, prefix="/api/v1/institutions", tags=["Campus billing"])
from app.routers import campus_action_center
app.include_router(campus_action_center.router, prefix="/api/v1/institutions", tags=["Campus Today"])
from app.routers import campus_control_plane
app.include_router(campus_control_plane.router, prefix="/api/v1/institutions", tags=["Campus control plane"])
from app.routers import admissions, tuition
app.include_router(admissions.router, prefix="/api/v1/institutions", tags=["Admissions"])
app.include_router(tuition.router, prefix="/api/v1/institutions", tags=["Tuition fees"])

from app.routers import brand_sharing
app.include_router(brand_sharing.router, prefix="/api/v1/share", tags=["Public share banners"])

@app.middleware("http")
async def private_campus_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/v1/institutions", "/api/v1/parents")):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Authorization, Cookie"
    return response

from app.routers import campus_learning
app.include_router(campus_learning.router, prefix="/api/v1/institutions", tags=["Private campus learning"])

from app.routers import campus_pilot
app.include_router(campus_pilot.router, prefix="/api/v1/institutions", tags=["Campus pilot"])
app.include_router(campus_pilot.webhook_router, prefix="/api/v1/whatsapp", tags=["WhatsApp webhooks"])
from app.routers import campus_exams
app.include_router(campus_exams.router, prefix="/api/v1/institutions", tags=["Campus exams"])
from app.routers import tuition_reminders
app.include_router(tuition_reminders.router, prefix="/api/v1/institutions", tags=["Tuition reminders"])
from app.routers import tuition_collection
app.include_router(tuition_collection.router, prefix="/api/v1/institutions", tags=["Tuition collection"])
from app.routers import campus_staff
app.include_router(campus_staff.router, prefix="/api/v1/institutions", tags=["Campus staff"])
from app.routers import campus_transport
app.include_router(campus_transport.router, prefix="/api/v1/institutions", tags=["Campus transport"])
from app.routers import campus_hostel
app.include_router(campus_hostel.router, prefix="/api/v1/institutions", tags=["Campus hostel"])
from app.routers import whatsapp
app.include_router(whatsapp.router, prefix="/api/v1/whatsapp", tags=["WhatsApp"])
