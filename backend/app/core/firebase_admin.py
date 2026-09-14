"""
Firebase Admin SDK initialization + helpers for mirroring backend users into
Firebase Authentication.

Design goals:
  * Lazy, single initialization (the Admin SDK app is a process-global).
  * Best-effort and non-fatal: if no service-account credential is configured,
    or the SDK fails to load, the helpers become no-ops that log a warning.
    Registration must never fail just because Firebase is unavailable.

Configure via FIREBASE_CREDENTIALS_PATH (preferred) or the standard
GOOGLE_APPLICATION_CREDENTIALS env var. Both should point at the
service-account JSON for the Firebase project.
"""
import asyncio
import logging
import os
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_initialized = False
_available = False


def _ensure_initialized() -> bool:
    """Initialize the Admin SDK once. Returns True if Firebase is usable."""
    global _initialized, _available
    if _initialized:
        return _available

    _initialized = True
    try:
        import firebase_admin
        from firebase_admin import credentials

        # Another part of the process may have initialized the default app.
        if firebase_admin._apps:
            _available = True
            return True

        cred_path = settings.FIREBASE_CREDENTIALS_PATH or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        options = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None

        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, options)
            logger.info("Firebase Admin SDK initialized from %s", cred_path)
        else:
            # Fall back to Application Default Credentials (e.g. GCP metadata).
            firebase_admin.initialize_app(options=options)
            logger.info("Firebase Admin SDK initialized with application default credentials")

        _available = True
    except Exception as e:
        _available = False
        logger.warning("Firebase Admin SDK not initialized; Firebase user sync disabled: %s", e)

    return _available


def send_course_event(course_id, action: str = "updated") -> bool:
    """Queue a course-updates push, without blocking an async caller.

    `messaging.send()` is a synchronous HTTPS round-trip to Firebase with no
    timeout. Every caller here is an `async def` endpoint, so calling it
    inline blocks the whole event loop — not merely the current request —
    for as long as Firebase takes to answer. That is what made publishing a
    course feel like it hung, and it stalled unrelated requests at the same
    time.

    The push is advisory (clients refetch on receipt), so when there is a
    running loop we hand the send to a worker thread and return immediately.
    The return value then means "queued", not "delivered"; no caller depends
    on delivery. Outside a loop (scripts, sync contexts) it still sends
    inline.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        loop.run_in_executor(None, _send_course_event_blocking, course_id, action)
        return True

    return _send_course_event_blocking(course_id, action)


def _send_course_event_blocking(course_id, action: str = "updated") -> bool:
    """
    Push a data-only FCM message to the 'course-updates' topic so app clients
    refetch the affected course (and the catalog) without the user pulling to
    refresh. Best-effort and non-fatal — a Firebase outage must never break an
    admin/instructor course edit.

    FCM data values must be strings. The message carries no `notification`
    block, so it is silent (no banner) and only triggers an in-app refresh.
    """
    if not _ensure_initialized():
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            topic="course-updates",
            data={
                "type": "course.updated",
                "action": str(action),
                "course_id": str(course_id),
            },
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "5"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(content_available=True),
                ),
            ),
        )
        messaging.send(message)
        logger.info("Sent course-updates FCM (course_id=%s action=%s)", course_id, action)
        return True
    except Exception as e:
        logger.warning("Failed to send course event FCM (course_id=%s): %s", course_id, e)
        return False


def create_firebase_user(
    email: str,
    password: str,
    display_name: str = "",
    email_verified: bool = False,
) -> Optional[str]:
    """
    Create a Firebase Authentication user mirroring a backend registration.

    Best-effort: returns the Firebase uid on success (or the existing uid if the
    email is already registered in Firebase), and None if Firebase is disabled
    or the call fails. Never raises — callers should not let Firebase break
    registration.
    """
    if not _ensure_initialized():
        return None

    try:
        from firebase_admin import auth as fb_auth

        try:
            user = fb_auth.create_user(
                email=email,
                password=password,
                display_name=display_name or None,
                email_verified=email_verified,
            )
            logger.info("Created Firebase user %s for %s", user.uid, email)
            return user.uid
        except fb_auth.EmailAlreadyExistsError:
            existing = fb_auth.get_user_by_email(email)
            logger.info("Firebase user already exists for %s: %s", email, existing.uid)
            return existing.uid
    except Exception as e:
        logger.warning("Failed to create Firebase user for %s: %s", email, e)
        return None
