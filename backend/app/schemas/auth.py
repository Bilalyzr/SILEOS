"""
Authentication Schemas - Pydantic models for auth endpoints
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # Six-digit TOTP code. Only consulted for accounts with 2FA enabled; the
    # client sends it on the second attempt after a 401 "otp_required".
    otp_code: Optional[str] = None

class TwoFactorCodeRequest(BaseModel):
    """A 6-digit TOTP code submitted to enable or disable 2FA."""
    code: str = Field(..., min_length=6, max_length=8)


class RegisterRequest(BaseModel):
    username: Optional[str] = None  # Optional - will be auto-generated from email if not provided
    email: EmailStr
    password: str
    first_name: str = ""
    last_name: str = ""
    phone: Optional[str] = None
    user_type: Optional[str] = "student"  # student or instructor

    # Instructor-specific fields (optional)
    designation: Optional[str] = None
    bio: Optional[str] = None
    experience: Optional[str] = None

    # Frontend validation fields (not used in backend)
    confirm_password: Optional[str] = None
    agree_to_terms: Optional[bool] = None

    # SS1 — optional referral code to join a cohort at registration time.
    referral_code: Optional[str] = None

    @validator('username', pre=True)
    def validate_username(cls, v):
        # Allow empty string or None - backend will auto-generate
        if not v or v == "":
            return None
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, periods, and hyphens')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict
    profile: Optional[dict] = None
    instructorProfile: Optional[dict] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    display_name: str
    role: str
    status: str
    message: Optional[str] = None
    # True when the account still needs email verification before login.
    # False when AUTO_VERIFY_EMAIL created an already-active account, so the
    # client can route straight to login instead of a verify-email screen.
    requires_verification: Optional[bool] = None
    # Whether two-factor auth (TOTP) is enrolled. Surface it so the Settings
    # page can show the correct badge without an extra round-trip.
    totp_enabled: Optional[bool] = None
    profile_completed: Optional[bool] = None

class RefreshTokenRequest(BaseModel):
    # Optional: sibling-subdomain session restore POSTs an empty body so the
    # server falls back to the shared-domain refresh cookie (see
    # /auth/refresh). A required field 422s before that fallback can run.
    refresh_token: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

class VerifyEmailRequest(BaseModel):
    token: str

class PasswordResetConfirmRequest(BaseModel):
    # Accept both snake_case and camelCase so the same endpoint works with
    # a snake_case backend convention and a camelCase frontend.
    token: str
    new_password: str = Field(..., alias="newPassword")

    model_config = {"populate_by_name": True}

    # Same complexity rules as RegisterRequest — a reset link must not be a
    # way around the password policy the registration form enforces.
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v