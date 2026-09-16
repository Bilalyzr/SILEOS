"""
Security utilities for JWT tokens and password hashing
"""

from datetime import datetime, timedelta
from typing import Any, Union, Optional, Iterable
import hashlib
import hmac
from jose import jwt, JWTError
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from passlib.hash import bcrypt, phpass

from .config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
# Hard 30-minute ceiling for admin "view as instructor" tokens. These
# tokens cannot be refreshed (see /auth/refresh handler) and cannot be
# used to start another impersonation (see /admin/impersonate handler).
IMPERSONATION_TOKEN_EXPIRE_MINUTES = 30


# --- Access-token revocation (logout denylist) ------------------------------
# JWTs are stateless, so without a server-side check a logged-out access
# token stayed valid until natural expiry (up to 30 min). On logout we now
# blacklist the token's SHA-256 in Redis for its remaining lifetime and
# get_current_user / get_optional_current_user refuse blacklisted tokens.
# Consistent with the rate limiter: if Redis is unavailable we FAIL OPEN
# (the denylist simply doesn't apply) rather than locking every user out.

_revocation_redis = None

def _get_revocation_redis():
    global _revocation_redis
    if _revocation_redis is None:
        import redis as _redis
        _revocation_redis = _redis.from_url(
            settings.REDIS_URL, decode_responses=True,
            socket_connect_timeout=0.3, socket_timeout=0.5,
        )
    return _revocation_redis

def revoke_all_user_sessions(user_id: int) -> None:
    """Reject every token issued to `user_id` BEFORE now. Logout then takes
    effect instantly on every origin (sibling-subdomain sessions live in
    per-origin localStorage that a logout on one origin cannot clear) and
    every device, not just the client that called /auth/logout."""
    try:
        _get_revocation_redis().setex(
            f"user_sessions_revoked:{user_id}",
            REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            str(int(datetime.utcnow().timestamp())),
        )
    except Exception:
        pass  # fail open — same policy as the token denylist

def is_session_revoked(payload: dict) -> bool:
    """True when the token predates the user's last global logout."""
    iat = payload.get("iat")
    if not iat:
        return False  # tokens minted before this feature age out naturally
    try:
        ts = _get_revocation_redis().get(f"user_sessions_revoked:{payload.get('sub')}")
        # >= (not >): a token minted in the SAME second as the logout must
        # die too — login→logout→refresh within one second otherwise slips
        # through the race window.
        return bool(ts and int(ts) >= int(iat))
    except Exception:
        return False

def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def revoke_access_token(token: str) -> None:
    """Blacklist `token` until its own `exp` (default: full access lifetime)."""
    try:
        ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            exp = payload.get("exp")
            if exp:
                remaining = int(exp - datetime.utcnow().timestamp())
                if remaining > 0:
                    ttl = remaining
        except JWTError:
            pass  # undecodable → keep default TTL; never extend past typical expiry
        _get_revocation_redis().setex(f"token_blacklist:{_token_fingerprint(token)}", ttl, "1")
    except Exception:
        pass  # fail open — revocation is best-effort, never blocks the logout itself

def is_token_revoked(token: str) -> bool:
    try:
        return _get_revocation_redis().get(f"token_blacklist:{_token_fingerprint(token)}") is not None
    except Exception:
        return False  # Redis down → fail open


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify native and explicitly supported legacy password hashes.

    WordPress migrations can leave three formats that the bcrypt-only
    ``CryptContext`` cannot identify. Treat unrecognised or malformed values as
    an authentication failure, never as an application error. The unsalted
    SHA-256 branch exists only for imported legacy accounts; callers should
    upgrade a successful legacy login to the native bcrypt format separately.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        if hashed_password.startswith("$wp$"):
            return bcrypt.verify(plain_password, hashed_password[4:])
        if hashed_password.startswith(("$P$", "$H$")):
            return phpass.verify(plain_password, hashed_password)
        if len(hashed_password) == 64:
            try:
                int(hashed_password, 16)
            except ValueError:
                return False
            candidate = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(candidate, hashed_password.lower())
        return pwd_context.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Only set type to "access" if not already specified in data
    # iat lets logout's per-user revocation reject tokens minted before it.
    to_encode.update({"exp": expire, "iat": int(datetime.utcnow().timestamp())})
    if "type" not in to_encode:
        to_encode["type"] = "access"

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": int(datetime.utcnow().timestamp()), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(
    token: str,
    expected_type: Optional[Union[str, Iterable[str]]] = "access",
) -> dict:
    """
    Verify and decode a JWT token.

    `expected_type` enforces token-type separation so a refresh / password-reset /
    email-verification token cannot be used as an access token. Pass `None` to
    skip the type check (only valid use case: code that intentionally inspects
    the type itself before continuing).

    Accepts either a single expected type (`"access"`) or an iterable of
    allowed types (`["access", "impersonation_access"]`) so callers like
    `get_current_user` can admit regular access tokens AND short-lived
    admin-impersonation tokens without accepting refresh / reset / verify
    tokens.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise JWTError("Could not validate credentials")

    if expected_type is not None:
        token_type = payload.get("type")
        if isinstance(expected_type, str):
            if token_type != expected_type:
                raise JWTError("Wrong token type")
        else:
            # Iterable of allowed types
            allowed = set(expected_type)
            if token_type not in allowed:
                raise JWTError("Wrong token type")

    return payload


def create_impersonation_token(target_user_id: int, admin_id: int) -> str:
    """
    Mint a short-lived impersonation access token. `sub` is the TARGET
    instructor id (so downstream code treats the request as that user);
    `impersonated_by` carries the acting admin id so we can reject
    chained impersonation and audit correctly. Hard 30-minute expiry —
    cannot be refreshed.
    """
    expire = datetime.utcnow() + timedelta(minutes=IMPERSONATION_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(target_user_id),
        "type": "impersonation_access",
        "impersonated_by": admin_id,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def create_email_verification_token(email: str) -> str:
    """Create email verification token"""
    data = {"sub": email, "type": "email_verification"}
    expire = datetime.utcnow() + timedelta(hours=24)
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGORITHM)

def create_password_reset_token(email: str) -> str:
    """Create password reset token"""
    data = {"sub": email, "type": "password_reset"}
    expire = datetime.utcnow() + timedelta(hours=1)
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=ALGORITHM)
