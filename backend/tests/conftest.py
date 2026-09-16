"""
Pytest fixtures for the LMS backend.

Uses an in-memory SQLite engine per test session so tests are deterministic
and never touch Postgres. The whole `Base.metadata` is created fresh for
each test, then dropped at teardown.
"""
# IMPORTANT: set test-friendly env vars BEFORE any `from app.*` imports
# so `get_settings()` doesn't barf on required fields and disabled
# middleware never engages during tests (rate-limit, request logging,
# IP whitelist would otherwise trip the TestClient's shared client IP).
import os

# IMPORTANT: Set required env vars BEFORE any app.* imports.
# Use exact values from the brief for test consistency.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "test-video-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

# Additional test-friendly overrides for middleware compatibility
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("RAZORPAY_KEY", "test-razorpay-key")
os.environ.setdefault("RAZORPAY_SECRET", "test-razorpay-secret")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")

# Force-disable middleware that would interfere with TestClient. Rate
# limiting in particular would 429 multiple `auth_headers(...)` calls
# from the same client IP within a single test run.
os.environ["ENABLE_API_RATE_LIMITING"] = "false"
os.environ["ENABLE_REQUEST_LOGGING"] = "false"
os.environ["ENABLE_IP_WHITELISTING"] = "false"

# TrustedHostMiddleware validates Host header — TestClient defaults to
# `testserver`, which would otherwise 400. Pydantic-settings parses
# List[str] env vars as JSON.
os.environ["ALLOWED_HOSTS"] = '["testserver","localhost","127.0.0.1"]'

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def authored_native_labs(db, make_user):
    """Test authored grading engines without resurrecting retired shipped labs."""
    import copy
    from app.models.content_library import VirtualLabCatalog
    from app.routers.virtual_labs import REACTION_LAB_BASICS, CELL_IDENTIFY, SKELETON_IDENTIFY
    from app.services.mastery_service import set_links
    owner = make_user(role='admin')
    definitions = [
        ('fixture-reaction-lab', 'Reaction Lab', 'chemistry', 'reaction_lab', REACTION_LAB_BASICS,
         ['balancing chemical equations', 'conservation of mass', 'stoichiometry']),
        ('fixture-cell-identify', 'Cell Biology', 'biology', 'identify_lab', CELL_IDENTIFY, ['cell biology', 'organelles']),
        ('fixture-skeleton-identify', 'Human Skeleton', 'biology', 'identify_lab', SKELETON_IDENTIFY, ['human skeleton', 'bones']),
    ]
    rows = []
    for slug, title, subject, template, config, concepts in definitions:
        row = VirtualLabCatalog(slug=slug, title=title, subject=subject, provider='native', native_template=template,
                                config=copy.deepcopy(config), is_published=True, created_by=owner.id)
        db.add(row); db.flush()
        set_links(db, 'lab', slug, concepts, user_id=owner.id)
        rows.append(row)
    db.commit()
    return rows
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Make `app.*` importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import database as core_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402


@asynccontextmanager
async def _noop_lifespan(_app):
    """Replace the production lifespan so init_db()/init_redis() never run."""
    yield


@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Importing models registers them on Base.metadata.
    from app import models  # noqa: F401
    core_db.Base.metadata.create_all(bind=eng)
    yield eng
    core_db.Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def TestingSessionLocal(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db(TestingSessionLocal):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(TestingSessionLocal):
    """FastAPI TestClient with the DB dependency overridden.

    Also overrides the FastAPI lifespan to a no-op so the production
    `init_db()` (which targets Postgres via the module-level engine) and
    `init_redis()` are never called during tests.
    """
    from app.main import app

    def _get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    # Set DB override BEFORE entering the TestClient context so startup
    # event handlers (and any request) see the test session.
    app.dependency_overrides[core_db.get_db] = _get_db

    # Swap the lifespan so init_db()/init_redis() never run.
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolate_redis():
    """Pin the Redis singleton to a fresh MockRedis for every test.

    Without this, a reachable broker on localhost:6379 (Docker Desktop keeps
    one up on the dev box) is silently used by the join-token rate limiter
    (INCR keys `rl:join-token:{user_id}`, 60s TTL) and the live-class reminder
    markers (SETNX keys keyed by class id, 2h TTL). Every test DB reuses ids
    1, 2, 3..., so state from earlier runs bled in as spurious 429s and
    "0 events" — the failures the handover misfiled as order-dependent
    flakes. The routers treat MockRedis as "unusable" and take their
    DB-backed fallback paths, which is what these tests were written against.
    """
    from app.core.redis import RedisClient, MockRedis
    previous = RedisClient._instance
    RedisClient._instance = MockRedis()
    try:
        yield
    finally:
        RedisClient._instance = previous


# ----- factory fixtures -----

@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _mk(role="student", email=None, password="Test@123", verified=True):
        """Create a User. The plaintext password is also stored on
        `u._test_password` so a test can call
        `auth_headers(u.user_email, u._test_password)` without having to
        remember the default magic string."""
        counter["n"] += 1
        n = counter["n"]
        from app.models.user import User
        u = User(
            user_login=f"user{n}",
            user_pass=get_password_hash(password),
            user_nicename=f"user{n}",
            user_email=email or f"user{n}@example.com",
            display_name=f"User {n}",
            role=role,
            is_active=True,
            is_verified=verified,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        u._test_password = password  # type: ignore[attr-defined]
        return u

    return _mk


@pytest.fixture
def make_company(db, make_user):
    counter = {"n": 0}

    def _mk(name=None, owner=None, approved=True):
        counter["n"] += 1
        n = counter["n"]
        owner = owner or make_user(role="company")
        from app.models.company import Company
        c = Company(
            owner_user_id=owner.id,
            name=name or f"Company {n}",
            slug=f"company-{n}",
            contact_email=owner.user_email,
            is_approved=approved,
            approval_source="admin_invite",
            approved_at=datetime.now(timezone.utc) if approved else None,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    return _mk


@pytest.fixture
def auth_headers(client):
    """Login and return Authorization header dict."""

    def _login(email, password="Test@123"):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


# ----- task 1 fixtures (from brief) -----


@pytest.fixture()
def student_user(db):
    """Create and persist a Student user."""
    from app.models.user import User
    u = User(
        user_login="student1",
        user_pass="x",
        user_nicename="student1",
        user_email="student1@example.com",
        display_name="student1",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def course(db):
    """Create and persist a Course owned by a separate instructor (not student_user).

    The course author and student enrollee must be distinct for payment/enrollment tests.
    """
    from app.models.user import User
    from app.models.course import Course

    # Create instructor author (separate identity from any student)
    instructor = User(
        user_login="instructor1",
        user_pass="x",
        user_nicename="instructor1",
        user_email="instructor1@example.com",
        display_name="instructor1",
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)

    # Create course owned by instructor
    c = Course(
        post_author=instructor.id,
        post_title="Test Course",
        course_price_type="paid",
        course_price=500.0,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def free_course(db):
    """Create and persist a free Course owned by an instructor."""
    from app.models.user import User
    from app.models.course import Course

    # Create instructor author
    author = User(
        user_login="instructor_free",
        user_pass="x",
        user_nicename="instructor_free",
        user_email="instructor_free@example.com",
        display_name="instructor_free",
    )
    db.add(author)
    db.commit()
    db.refresh(author)

    # Create free course
    c = Course(post_author=author.id, post_title="Free Course",
               course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def order_row(db, student_user):
    """Create and persist an Order for the student_user."""
    from app.models.payment import Order, OrderStatus

    o = Order(user_id=student_user.id, order_key="RZP_FIXTURE",
              order_status=OrderStatus.COMPLETED, total_amount=500)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@pytest.fixture()
def as_user():
    """Override auth to act as the given user. Usage: as_user(student_user)."""
    from app.services.auth_service import AuthService
    from app.main import app

    def _impl(user_obj):
        app.dependency_overrides[AuthService.get_current_active_user] = lambda: user_obj
        app.dependency_overrides[AuthService.get_optional_current_user] = lambda: user_obj   # public-preview endpoints take an optional user
        app.dependency_overrides[AuthService.require_admin] = lambda: user_obj
        return user_obj

    yield _impl
    app.dependency_overrides.pop(AuthService.get_current_active_user, None)
    app.dependency_overrides.pop(AuthService.get_optional_current_user, None)
    app.dependency_overrides.pop(AuthService.require_admin, None)
