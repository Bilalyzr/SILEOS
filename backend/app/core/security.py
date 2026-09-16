"""
Security utilities for JWT tokens and password hashing
"""

from datetime import datetime, timedelta
from typing import Any, Union, Optional, Iterable
from jose import jwt, JWTError
from passlib.context import CryptContext
from passlib.hash import bcrypt

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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

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
    to_encode.update({"exp": expire})
    if "type" not in to_encode:
        to_encode["type"] = "access"

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
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