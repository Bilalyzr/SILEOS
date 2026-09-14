"""
TOTP (RFC 6238) helpers for admin two-factor authentication.

Kept deliberately thin: generate a secret, build the provisioning URI an
authenticator app can scan, and verify a submitted code. Enforcement lives in
the auth router; enrolment state lives on User.totp_secret / User.totp_enabled.

`pyotp` is an optional import so that a deployment which has not yet installed
it degrades to "2FA unavailable" rather than failing to boot — the same
best-effort posture the Firebase helper uses. is_available() lets callers
surface a clear error instead of a 500.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ISSUER = "SashaInfinity LMS"

try:  # pragma: no cover - import guard
    import pyotp

    _AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    pyotp = None  # type: ignore[assignment]
    _AVAILABLE = False
    logger.warning("pyotp is not installed — TOTP two-factor auth is unavailable")


def is_available() -> bool:
    """True when the TOTP backend can actually be used."""
    return _AVAILABLE


def generate_secret() -> str:
    """Return a fresh base32 secret for a new enrolment."""
    if not _AVAILABLE:
        raise RuntimeError("pyotp is not installed")
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_name: str) -> str:
    """Build the otpauth:// URI an authenticator app scans as a QR code."""
    if not _AVAILABLE:
        raise RuntimeError("pyotp is not installed")
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=ISSUER)


def verify(secret: Optional[str], code: Optional[str], valid_window: int = 1) -> bool:
    """Check a submitted 6-digit code against the secret.

    `valid_window=1` accepts the adjacent 30s steps, which absorbs ordinary
    clock drift between the server and the user's phone. Returns False rather
    than raising on any malformed input so callers can treat it as a plain
    auth failure.
    """
    if not _AVAILABLE or not secret or not code:
        return False
    cleaned = str(code).strip().replace(" ", "")
    if not cleaned.isdigit():
        return False
    try:
        return pyotp.TOTP(secret).verify(cleaned, valid_window=valid_window)
    except Exception:
        logger.exception("TOTP verification raised unexpectedly")
        return False
