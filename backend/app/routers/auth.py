"""
Authentication Router - SashaInfinity LMS API
Handles user authentication, registration, and token management
"""

from datetime import timedelta, datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.models.user import User, UserProfile, InstructorProfile
from app.services.auth_service import AuthService
from app.core.firebase_admin import create_firebase_user
from app.core import totp
from app.utils.email import (
    send_login_notification_email,
    send_password_reset_email,
    send_verification_email,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TwoFactorCodeRequest,
    VerifyEmailRequest
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Marker stored in User.user_activation_key while a password-reset token is
# outstanding ("<prefix><jti>"). The column exists in the schema already (the
# WordPress-style activation key) and nothing else writes it, so it gives the
# reset flow durable, single-use token state without Redis or a migration.
_RESET_KEY_PREFIX = "pwdreset:"
_SSO_REFRESH_COOKIE = "sasha_sso_refresh"


def _shared_cookie_domain(request: Request) -> Optional[str]:
    host = (request.url.hostname or "").lower()
    return ".sashainfinity.com" if host == "sashainfinity.com" or host.endswith(".sashainfinity.com") else None


def _set_shared_session(response: Response, request: Request, refresh_token: str) -> None:
    domain = _shared_cookie_domain(request)
    response.set_cookie(
        key=_SSO_REFRESH_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
        domain=domain,
        secure=domain is not None,
        httponly=True,
        samesite="lax",
    )


def _clear_shared_session(response: Response, request: Request) -> None:
    domain = _shared_cookie_domain(request)
    response.delete_cookie(
        key=_SSO_REFRESH_COOKIE,
        path="/api/v1/auth",
        domain=domain,
        secure=domain is not None,
        httponly=True,
        samesite="lax",
    )

@router.post("/login", response_model=TokenResponse)
@router.post("/login/", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    User login endpoint (handles both /login and /login/)
    Returns access token and refresh token
    """
    # First check if user exists (to provide better error message for unverified users)
    existing_user = db.query(User).filter(User.user_email == request.email).first()

    # If user exists but not verified, show verification message instead of "email not found".
    # AUTO_VERIFY_EMAIL (dev) bypasses the gate so accounts registered before the flag was
    # enabled — whose is_verified is still False — can still log in without DB surgery.
    if existing_user and not existing_user.is_verified and not settings.AUTO_VERIFY_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in. Check your inbox for the verification email.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Authenticate user
    user, auth_error = AuthService.authenticate_user(db, request.email, request.password)
    if not user:
        # Anti-enumeration: unknown email and wrong password return the SAME
        # 401 with one generic message, so an attacker cannot distinguish
        # "account exists" from "bad password". The service still returns
        # distinct codes internally (auth_error) for logging/lockout logic.
        if auth_error in ("email_not_found", "incorrect_password"):
            if auth_error == "email_not_found":
                logger.info("Login failed: unknown email")
            else:
                logger.info("Login failed: wrong password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif auth_error == "instructor_not_approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your instructor account is pending approval. Please wait for admin approval to access the system.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Double-check email is verified (in case authenticate_user didn't catch it).
    # Same AUTO_VERIFY_EMAIL bypass as the pre-auth check above.
    if not user.is_verified and not settings.AUTO_VERIFY_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in. Check your inbox for the verification email.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Two-factor gate. Only accounts that completed enrolment (totp_enabled)
    # are challenged, so turning this on cannot lock out an admin who has not
    # set up an authenticator yet. The password has already been verified at
    # this point; the code is a second factor, not a replacement.
    #
    # Privileged roles (admin + superadmin) are held to a stricter standard:
    # 2FA is *mandatory*. An account in either role that somehow lost
    # totp_enabled is refused outright rather than silently allowed through
    # the soft gate below.
    if user.role in ("admin", "superadmin") and not getattr(user, "totp_enabled", False):
        logger.warning("%s login blocked — 2FA not enabled (user_id=%s)", user.role, user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Two-factor authentication is required for {user.role.capitalize()} accounts.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if getattr(user, "totp_enabled", False):
        if not request.otp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                # Distinct machine-readable marker so the client knows to show
                # the code field rather than treating this as a bad password.
                detail="otp_required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not totp.verify(user.totp_secret, request.otp_code):
            logger.warning("Failed TOTP attempt for user_id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication code. Please try again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Get user profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    # Get instructor profile if user is instructor
    instructor_profile = None
    if user.role == "instructor":
        instructor_profile = db.query(InstructorProfile).filter(
            InstructorProfile.user_id == user.id
        ).first()

    # Update last_login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.user_email,
            "login": user.user_login,
            "display_name": user.display_name,
            "role": user.role,
            "profile_completed": user.profile_completed,
            "totp_enabled": bool(user.totp_enabled)
        },
        "profile": {
            "id": profile.id if profile else None,
            "user_id": profile.user_id if profile else None,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "phone": profile.phone if profile else "",
            "description": profile.description if profile else "",
            "designation": profile.designation if profile else "",
            "address": profile.address if profile else "",
            "city": profile.city if profile else "",
            "state": profile.state if profile else "",
            "country": profile.country if profile else "",
            "postal_code": profile.postal_code if profile else "",
            "profile_photo": profile.profile_photo if profile else "",
            "cover_photo": profile.cover_photo if profile else "",
            "facebook": profile.facebook if profile else "",
            "twitter": profile.twitter if profile else "",
            "linkedin": profile.linkedin if profile else "",
            "website": profile.website if profile else "",
            "show_email": profile.show_email if profile else False,
            "receive_notifications": profile.receive_notifications if profile else True
        } if profile else None,
        "instructorProfile": {
            "is_approved": instructor_profile.is_approved if instructor_profile else False,
            "bio": instructor_profile.instructor_bio if instructor_profile else "",
            "designation": instructor_profile.instructor_designation if instructor_profile else ""
        } if instructor_profile else None
    }

# ---------------------------------------------------------------------------
# Two-factor authentication (TOTP)
#
# Enrolment is deliberately two-step: /2fa/setup stores a secret but leaves
# totp_enabled False, and only /2fa/enable — which requires a working code —
# turns enforcement on. That ordering means a user who scans the QR but never
# finishes (or loses their phone mid-setup) is never locked out.
# ---------------------------------------------------------------------------

@router.post("/2fa/setup")
async def setup_two_factor(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Begin TOTP enrolment: issue a secret + otpauth URI to render as a QR."""
    if not totp.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Two-factor authentication is not available on this server (pyotp missing)",
        )

    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled. Disable it first to re-enrol.",
        )

    secret = totp.generate_secret()
    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.commit()

    return {
        "secret": secret,
        "otpauth_uri": totp.provisioning_uri(secret, current_user.user_email),
        "message": "Scan this in your authenticator app, then confirm a code to enable.",
    }


@router.get("/2fa/qr")
async def two_factor_qr(
    current_user: User = Depends(AuthService.get_current_active_user),
) -> Any:
    """
    Render the pending TOTP enrolment secret as a PNG QR code, so the
    frontend can show it in an <img> without a client-side QR dependency.
    Only meaningful between /2fa/setup and /2fa/enable (i.e. when a secret
    exists but is not yet enabled). Returns 409 if enrolment isn't pending.
    """
    if not current_user.totp_secret or current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No pending 2FA setup. Call /2fa/setup first.",
        )
    try:
        import io
        import qrcode
        from fastapi.responses import StreamingResponse

        uri = totp.provisioning_uri(current_user.totp_secret, current_user.user_email)
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR rendering unavailable (qrcode library missing).",
        )


@router.post("/2fa/enable")
async def enable_two_factor(
    payload: TwoFactorCodeRequest,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Finish enrolment by proving the authenticator produces valid codes."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start setup first — no pending secret for this account.",
        )

    if not totp.verify(current_user.totp_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That code did not match. Check your device's clock and try again.",
        )

    current_user.totp_enabled = True
    db.commit()
    logger.info("2FA enabled for user_id=%s", current_user.id)
    return {"message": "Two-factor authentication enabled", "totp_enabled": True}


@router.post("/2fa/disable")
async def disable_two_factor(
    payload: TwoFactorCodeRequest,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Turn 2FA off. Requires a current code so a hijacked session can't."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled.",
        )

    if not totp.verify(current_user.totp_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That code did not match.",
        )

    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()
    logger.info("2FA disabled for user_id=%s", current_user.id)
    return {"message": "Two-factor authentication disabled", "totp_enabled": False}


@router.get("/2fa/status")
async def two_factor_status(
    current_user: User = Depends(AuthService.get_current_active_user),
) -> Any:
    """Whether 2FA is enabled for the caller, and whether the server supports it."""
    return {
        "totp_enabled": bool(current_user.totp_enabled),
        "available": totp.is_available(),
    }


@router.post("/register-instructor", response_model=UserResponse)
@router.post("/register-instructor/", response_model=UserResponse)
async def register_instructor(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    Instructor registration endpoint - creates instructor with pending approval
    """
    logger.info("Instructor registration request received for %s", request.email)

    # Check if user already exists
    existing_user = db.query(User).filter(User.user_email == request.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Create new user
    hashed_password = get_password_hash(request.password)

    # Generate username from email if not provided
    username = request.username
    if not username:
        username = request.email.split('@')[0]
        # Ensure username is unique
        counter = 1
        original_username = username
        while db.query(User).filter(User.user_login == username).first():
            username = f"{original_username}{counter}"
            counter += 1

    # ALWAYS create as instructor
    new_user = User(
        user_login=username,
        user_email=request.email,
        user_pass=hashed_password,
        user_nicename=username.lower().replace(' ', '-'),
        display_name=request.first_name + " " + request.last_name,
        user_status=1,  # 1 = active
        role="instructor",  # FORCE instructor role
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create user profile
    user_profile = UserProfile(
        user_id=new_user.id,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone or "",
        description="",
        profile_photo="",
        designation=request.designation or ""
    )

    db.add(user_profile)
    db.commit()

    # Create instructor profile (REQUIRED - pending approval)
    instructor_profile = InstructorProfile(
        user_id=new_user.id,
        instructor_bio=request.bio or "",
        instructor_designation=request.designation or "",
        is_approved=False,  # Requires admin approval
        is_blocked=False,
        profile_completion=50 if (request.bio and request.designation) else 0
    )
    db.add(instructor_profile)
    db.commit()

    logger.info(
        "Instructor created: email=%s profile_id=%s approved=%s",
        new_user.user_email, instructor_profile.id, instructor_profile.is_approved,
    )

    # Capture before the DB session closes (background tasks run post-response).
    _email = new_user.user_email
    _display = new_user.display_name
    _uid = new_user.id

    # Mirror the account into Firebase Authentication (best-effort, non-fatal),
    # in a background thread so its blocking HTTP call can't stall the response.
    background_tasks.add_task(
        create_firebase_user,
        email=_email,
        password=request.password,
        display_name=_display,
    )

    # Send verification email after responding — a slow SMTP server must not
    # time out the register call.
    verification_token = create_access_token(
        data={"sub": str(_uid), "type": "email_verification"},
        expires_delta=timedelta(hours=24)
    )
    background_tasks.add_task(
        send_verification_email, _email, verification_token, _display
    )

    return {
        "id": new_user.id,
        "email": new_user.user_email,
        "username": new_user.user_login,
        "display_name": new_user.display_name,
        "role": new_user.role,
        "status": "active",
        "message": "Registration successful! Please check your email to verify your account. Your instructor account is pending admin approval."
    }

@router.get("/check-email")
async def check_email(
    email: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Check if email is already registered
    """
    existing_user = db.query(User).filter(User.user_email == email).first()
    return {"exists": existing_user is not None}

@router.post("/register", response_model=UserResponse)
@router.post("/register/", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    User registration endpoint
    Creates new user account
    """
    logger.info(
        "Registration request received for %s (user_type=%s)",
        request.email, getattr(request, "user_type", "student"),
    )

    # Check if user already exists
    existing_user = db.query(User).filter(User.user_email == request.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Create new user
    hashed_password = get_password_hash(request.password)

    # Determine role - default to student
    user_role = getattr(request, 'user_type', 'student')
    if user_role not in ['student', 'instructor']:
        user_role = 'student'

    # Generate username from email if not provided
    username = request.username
    if not username:
        username = request.email.split('@')[0]
        # Ensure username is unique
        counter = 1
        original_username = username
        while db.query(User).filter(User.user_login == username).first():
            username = f"{original_username}{counter}"
            counter += 1

    # Single transactional block: user + profile + (optional) instructor profile
    # + (optional) referral redemption. Any failure rolls back the whole thing
    # so we never leave a half-registered account behind.
    referral_code_raw = getattr(request, "referral_code", None)
    try:
        new_user = User(
            user_login=username,
            user_email=request.email,
            user_pass=hashed_password,
            user_nicename=username.lower().replace(' ', '-'),
            display_name=((request.first_name + " " + request.last_name).strip()) or request.email.split('@')[0],
            user_status=1,  # 1 = active
            role=user_role,
            is_active=True,
            # Dev convenience (AUTO_VERIFY_EMAIL): skip the email-verification gate.
            is_verified=settings.AUTO_VERIFY_EMAIL,
        )
        db.add(new_user)
        db.flush()  # need new_user.id for FKs below

        user_profile = UserProfile(
            user_id=new_user.id,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone or "",
            description="",
            profile_photo="",
            designation=request.designation or "" if user_role == 'instructor' else ""
        )
        db.add(user_profile)
        db.flush()

        if user_role == 'instructor':
            instructor_profile = InstructorProfile(
                user_id=new_user.id,
                instructor_bio=request.bio or "",
                instructor_designation=request.designation or "",
                is_approved=False,  # Requires admin approval
                is_blocked=False,
                profile_completion=50 if (request.bio and request.designation) else 0
            )
            db.add(instructor_profile)
            db.flush()

        # --- SS1: Referral-code cohort join + auto-enroll -------------
        if referral_code_raw:
            from app.models.cohort import Cohort, ReferralCode, CohortMembership
            from app.models.enrollment import Enrollment
            from app.services.coupon_service import lock_referral_and_bump
            from datetime import datetime as _dt, timezone as _tz

            # Case-insensitive lookup to match Batch 1's checkout paths.
            code_row = db.query(ReferralCode).filter(
                ReferralCode.code.ilike(referral_code_raw.strip())
            ).first()
            if not code_row:
                raise ValueError("Invalid referral code")

            # Timezone-aware expiry check
            if code_row.expires_at is not None:
                now_utc = _dt.now(_tz.utc)
                exp = code_row.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=_tz.utc)
                if exp < now_utc:
                    raise ValueError("Referral code has expired")
            if code_row.max_uses and (code_row.used_count or 0) >= code_row.max_uses:
                raise ValueError("Referral code exhausted")

            cohort = db.query(Cohort).filter(Cohort.id == code_row.cohort_id).first()
            if not cohort or not cohort.is_active:
                raise ValueError("Cohort is not active")

            # Membership + auto-enroll
            membership = CohortMembership(cohort_id=cohort.id, user_id=new_user.id)
            db.add(membership)

            existing_enr = db.query(Enrollment).filter(
                Enrollment.user_id == new_user.id,
                Enrollment.course_id == cohort.course_id,
            ).first()
            if not existing_enr:
                enr = Enrollment(
                    course_id=cohort.course_id,
                    user_id=new_user.id,
                    enrollment_status="enrolled",
                    cohort_id=cohort.id,
                )
                db.add(enr)
            elif getattr(existing_enr, "cohort_id", None) is None:
                existing_enr.cohort_id = cohort.id

            # Atomic used_count bump under SELECT FOR UPDATE
            lock_referral_and_bump(db, code_row.id)

        db.commit()
        db.refresh(new_user)
    except HTTPException:
        db.rollback()
        raise
    except ValueError as ref_exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Referral code rejected: {ref_exc}",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {e}",
        )

    # Capture values before the request-scoped DB session closes — background
    # tasks run AFTER the response is sent, so new_user may be detached by then.
    _email = new_user.user_email
    _display = new_user.display_name
    _uid = new_user.id

    # Mirror the account into Firebase Authentication (best-effort, non-fatal).
    # Runs in a background thread so the slow/blocking Firebase HTTP call never
    # holds up the response or blocks the event loop.
    background_tasks.add_task(
        create_firebase_user,
        email=_email,
        password=request.password,
        display_name=_display,
        email_verified=settings.AUTO_VERIFY_EMAIL,
    )

    # Send verification email after responding (skipped when auto-verified in dev).
    # Backgrounding it means a slow SMTP server can't time out the register call.
    if not settings.AUTO_VERIFY_EMAIL:
        verification_token = create_access_token(
            data={"sub": str(_uid), "type": "email_verification"},
            expires_delta=timedelta(hours=24)
        )
        background_tasks.add_task(
            send_verification_email, _email, verification_token, _display
        )

    # Different messages for instructors vs students
    if user_role == 'instructor':
        message = "Registration successful! Your instructor account is pending admin approval. You will be notified once approved."
    elif settings.AUTO_VERIFY_EMAIL:
        message = "Registration successful. You can now log in."
    else:
        message = "Registration successful. Please check your email to verify your account."

    return {
        "id": new_user.id,
        "email": new_user.user_email,
        "username": new_user.user_login,
        "display_name": new_user.display_name,
        "role": new_user.role,
        "status": "active" if new_user.is_active else "inactive",
        "message": message,
        # Lets the client skip the verify-email screen when auto-verified.
        "requires_verification": not new_user.is_verified,
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token
    """
    try:
        supplied_token = payload.refresh_token or request.cookies.get(_SSO_REFRESH_COOKIE)
        if not supplied_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")
        claims = verify_token(supplied_token, expected_type="refresh")
        user_id = claims.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Defense-in-depth: impersonation tokens must never be refreshable.
        # verify_token(expected_type="refresh") already rejects non-refresh
        # tokens, but we double-check here so a future refactor that loosens
        # the type check can't accidentally re-open this door.
        if claims.get("type") == "impersonation_access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Impersonation tokens cannot be refreshed",
            )

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        _set_shared_session(response, request, supplied_token)
        return {
            "access_token": access_token,
            "refresh_token": supplied_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "email": user.user_email,
                "login": user.user_login,
                "display_name": user.display_name,
                "role": user.role
            }
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/sso")
async def establish_shared_session(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Any:
    """Place a validated refresh token in the shared Sasha domain cookie."""
    token = payload.refresh_token
    if not token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="refresh_token is required")
    try:
        claims = verify_token(token, expected_type="refresh")
        user_id = claims.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
        if not user or not user.is_active:
            raise ValueError("inactive or missing user")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from None
    _set_shared_session(response, request, token)
    return {"shared_session": True}

@router.post("/resend-verification")
async def resend_verification_email(
    request: dict,
    db: Session = Depends(get_db),
) -> Any:
    """
    Re-send the email-verification link.

    Body: {"email": "..."}. Returns a generic success message whether or not
    the account exists / is already verified, so attackers can't enumerate
    accounts. The actual email is only dispatched if the account exists and
    is unverified.

    Intended use cases:
      1. User hits login while still unverified — frontend surfaces a
         "Resend verification email" button that calls this endpoint.
      2. Admin 'Resend verification' action on the users table, for users
         whose original mail was lost (e.g. during an SMTP outage).
    """
    email = (request.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    generic_ok = {"message": "If the account exists and needs verification, a new email has been sent."}

    user = db.query(User).filter(User.user_email == email).first()
    if not user:
        return generic_ok
    if user.is_verified:
        return generic_ok

    try:
        token = create_access_token(
            data={"sub": str(user.id), "type": "email_verification"},
            expires_delta=timedelta(hours=24),
        )
        await send_verification_email(user.user_email, token, user.display_name)
    except Exception as e:
        logger.error("resend-verification error: %s", e)
        # Still return generic success — don't leak internals.

    return generic_ok


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify user email address
    """
    try:
        # Get token from request body
        token = request.token

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required"
            )

        payload = verify_token(token, expected_type="email_verification")

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "email_verification":
            logger.warning(
                "Email verification rejected: invalid token type=%s", token_type
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            logger.warning("Email verification: user id %s not found", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if already verified
        if user.is_verified:
            logger.info("User %s already verified", user.user_email)
            return {"message": "Email has already been verified. You can proceed to login."}

        # Mark email as verified
        user.is_verified = True
        user.is_active = True
        user.user_status = 1  # Set to active (1 = active)
        db.commit()

        logger.info("User %s verified successfully", user.user_email)
        return {"message": "Email verified successfully. Your account is now active."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Email verification error: %s: %s", type(e).__name__, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Send password reset email
    """
    user = db.query(User).filter(User.user_email == request.email).first()

    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a password reset link has been sent."}

    # Create password reset token. The jti makes the token SINGLE-USE: it is
    # also persisted on the user row (user_activation_key — the WP-style
    # column this schema already ships) and cleared on use, so a replayed
    # token is rejected even though the JWT itself is still unexpired.
    reset_jti = secrets.token_urlsafe(24)
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset", "jti": reset_jti},
        expires_delta=timedelta(hours=1)
    )
    user.user_activation_key = f"{_RESET_KEY_PREFIX}{reset_jti}"
    db.commit()

    await send_password_reset_email(user.user_email, reset_token)

    return {"message": "If the email exists, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirmRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset user password using reset token (single-use).

    A reset token carries a jti that must match the marker stored on the
    user at issue time; the marker is cleared on use, so replaying a token
    (or using one superseded by a newer request) is rejected.
    """
    try:
        token = request.token
        new_password = request.new_password
        payload = verify_token(token, expected_type="password_reset")
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Single-use enforcement: the jti must match the marker stored at
        # issue time. It is cleared below, so a second presentation of the
        # same token (or any older one) fails here.
        token_jti = payload.get("jti")
        if not token_jti or user.user_activation_key != f"{_RESET_KEY_PREFIX}{token_jti}":
            logger.warning(
                "Rejected reset token for user_id=%s: unknown/already-used jti", user.id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used reset token"
            )

        # Update password and consume the token in the same commit.
        user.user_pass = get_password_hash(new_password)
        user.user_activation_key = ""
        db.commit()

        return {"message": "Password reset successfully"}

    except HTTPException:
        # Raised deliberately above — keep its status/detail instead of
        # masking them with the generic catch-all below.
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Change user password (requires authentication)
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.user_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Get user in this session and update password
    user = db.query(User).filter(User.id == current_user.id).first()
    if user:
        user.user_pass = get_password_hash(request.new_password)
        db.commit()

    return {"message": "Password changed successfully"}

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """
    Logout user (client should remove tokens)
    """
    _clear_shared_session(response, request)
    # Revoke the presented access token so it cannot keep calling the API
    # until natural expiry. (The denylist entry self-expires at the token's
    # own `exp` — see app/core/security.py.)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        from app.core.security import revoke_access_token
        revoke_access_token(auth_header[7:].strip())
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get current user information with profile
    """
    # Get user profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    # Get instructor profile if user is instructor
    instructor_profile = None
    if current_user.role == "instructor":
        instructor_profile = db.query(InstructorProfile).filter(
            InstructorProfile.user_id == current_user.id
        ).first()

    return {
        "id": current_user.id,
        "email": current_user.user_email,
        "username": current_user.user_login,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "status": "active" if current_user.is_active else "suspended" if current_user.user_status == 2 else "inactive",
        "profile_completed": current_user.profile_completed,
        "totp_enabled": bool(current_user.totp_enabled),
        "profile": {
            "id": profile.id if profile else None,
            "user_id": profile.user_id if profile else None,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "phone": profile.phone if profile else "",
            "description": profile.description if profile else "",
            "designation": profile.designation if profile else "",
            "address": profile.address if profile else "",
            "city": profile.city if profile else "",
            "state": profile.state if profile else "",
            "country": profile.country if profile else "",
            "postal_code": profile.postal_code if profile else "",
            "profile_photo": profile.profile_photo if profile else "",
            "cover_photo": profile.cover_photo if profile else "",
            "facebook": profile.facebook if profile else "",
            "twitter": profile.twitter if profile else "",
            "linkedin": profile.linkedin if profile else "",
            "website": profile.website if profile else "",
            "show_email": profile.show_email if profile else False,
            "receive_notifications": profile.receive_notifications if profile else True
        } if profile else None,
        "instructorProfile": {
            "is_approved": instructor_profile.is_approved if instructor_profile else False,
            "bio": instructor_profile.instructor_bio if instructor_profile else "",
            "designation": instructor_profile.instructor_designation if instructor_profile else ""
        } if instructor_profile else None
    }

import os
import httpx
import jwt
import requests
import json
import re
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

def verify_firebase_token(id_token: str) -> dict:
    """
    Verify Firebase ID token using Google's public certificates.
    Does not require Firebase Admin SDK service account credentials.
    """
    project_id = os.getenv("FIREBASE_PROJECT_ID", "sashainfinity-720cb")

    try:
        # Decode header to get kid (key ID)
        header = jwt.get_unverified_header(id_token)
        kid = header.get('kid')

        if not kid:
            logger.error("verify_firebase_token: No kid in token header")
            raise ValueError("Invalid token - no key ID in header")

        # Get Google's public keys for Firebase (X.509 certificates)
        keys_url = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
        keys_response = requests.get(keys_url, timeout=10)
        keys_response.raise_for_status()
        keys = keys_response.json()

        # Find matching certificate by kid
        if kid not in keys:
            logger.error(f"verify_firebase_token: kid {kid} not in Google keys")
            raise ValueError("Invalid token - key not found in Google's certificates")

        cert_pem = keys[kid]

        # Extract public key from X.509 certificate
        cert = load_pem_x509_certificate(cert_pem.encode('utf-8'), default_backend())
        public_key = cert.public_key()

        # Convert to PEM format for PyJWT
        public_key_pem = public_key.public_bytes(
            Encoding.PEM,
            PublicFormat.SubjectPublicKeyInfo
        )

        # Verify token signature and claims
        decoded = jwt.decode(
            id_token,
            public_key_pem,
            algorithms=['RS256'],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={'verify_exp': True}
        )

        logger.info(f"verify_firebase_token: Token verified for {decoded.get('email', 'unknown')}")
        return decoded

    except jwt.ExpiredSignatureError as e:
        logger.error(f"verify_firebase_token: Token expired: {e}")
        raise ValueError("Token has expired")
    except jwt.InvalidAlgorithmError as e:
        logger.error(f"verify_firebase_token: Invalid algorithm: {e}")
        raise ValueError(f"Invalid token algorithm: {str(e)}")
    except jwt.InvalidAudienceError as e:
        logger.error(f"verify_firebase_token: Invalid audience: {e}")
        raise ValueError(f"Invalid token audience: {str(e)}")
    except jwt.InvalidIssuerError as e:
        logger.error(f"verify_firebase_token: Invalid issuer: {e}")
        raise ValueError(f"Invalid token issuer: {str(e)}")
    except jwt.InvalidKeyError as e:
        logger.error(f"verify_firebase_token: Invalid key: {e}")
        raise ValueError(f"Invalid public key: {str(e)}")
    except jwt.InvalidTokenError as e:
        logger.error(f"verify_firebase_token: Invalid token: {e}")
        raise ValueError(f"Invalid token: {str(e)}")
    except requests.RequestException as e:
        logger.error(f"verify_firebase_token: Failed to fetch Google certs: {e}")
        raise ValueError(f"Failed to fetch Google certificates: {str(e)}")
    except ValueError as e:
        # Re-raise ValueError with message
        logger.error(f"verify_firebase_token: ValueError: {e}")
        raise
    except Exception as e:
        # Catch-all for unexpected errors (cryptography, network, etc.)
        logger.exception(f"verify_firebase_token unexpected error: {type(e).__name__}: {e}")
        raise ValueError(f"Token verification failed: {str(e)}")


# Federated identity providers whose logins this backend accepts. Firebase
# projects can mint ID tokens for many providers (phone, anonymous, custom
# auth); only the ones explicitly wired into a federated endpoint belong here.
FEDERATED_SIGN_IN_PROVIDERS = {"google.com"}


def _validate_federated_claims(decoded_token: dict) -> None:
    """Reject federated ID tokens whose claims we do not accept.

    Runs AFTER signature verification (verify_firebase_token) and BEFORE any
    account lookup or token minting, so a rejected claim can never touch the
    database. Raises 403 when:

    * ``email_verified`` is not exactly ``True`` — a signature-valid token for
      an unverified provider identity must not reach account lookup;
    * ``firebase.sign_in_provider`` is not in FEDERATED_SIGN_IN_PROVIDERS —
      other tenants/providers of the same Firebase project (anonymous, phone,
      password) must not ride the Google endpoint.
    """
    if decoded_token.get("email_verified") is not True:
        logger.warning(
            "Federated login rejected: email_verified=%r", decoded_token.get("email_verified")
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address not verified with the identity provider",
        )

    firebase_claims = decoded_token.get("firebase")
    if not isinstance(firebase_claims, dict):
        firebase_claims = {}
    provider = firebase_claims.get("sign_in_provider")
    if provider not in FEDERATED_SIGN_IN_PROVIDERS:
        logger.warning("Federated login rejected: sign_in_provider=%r", provider)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unsupported sign-in provider",
        )


def _federated_totp_gate(user: User, otp_code: Optional[str]) -> None:
    """Apply the password-login 2FA gate (see /login ~117-139) to federated
    logins of an EXISTING matched account.

    Without this, Google sign-in minted full access+refresh tokens for a
    totp_enabled account with no code challenge — a 2FA bypass for exactly
    the accounts that opted into (or are required to use) it. The responses
    deliberately mirror /login field-for-field ("otp_required" 401 with the
    WWW-Authenticate header, then inline code verification on re-submit), so
    the frontend 2FA screen works unchanged; the federated completion step
    is re-submitting the same endpoint with ``otp_code`` added.
    """
    # Privileged roles: 2FA is mandatory — same stricter standard as /login.
    if user.role in ("admin", "superadmin") and not getattr(user, "totp_enabled", False):
        logger.warning(
            "%s federated login blocked — 2FA not enabled (user_id=%s)", user.role, user.id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Two-factor authentication is required for {user.role.capitalize()} accounts.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if getattr(user, "totp_enabled", False):
        if not otp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                # Same machine-readable marker as /login: the client should
                # show the code field, not treat this as a failed sign-in.
                detail="otp_required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not totp.verify(user.totp_secret, otp_code):
            logger.warning("Failed TOTP attempt on federated login for user_id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication code. Please try again.",
                headers={"WWW-Authenticate": "Bearer"},
            )


def normalize_mobile_number(raw: Any) -> str:
    """
    Validate and normalise a mobile number to a bare 10-digit Indian number.

    Google sign-in never gives us a phone number, so it is collected from the
    user instead — at signup for brand-new Google accounts, and via the
    one-time prompt (/auth/phone) for accounts created before this was
    mandatory. Accepts an optional +91/0091/91/0 prefix and any spacing or
    dashes; stores digits only so lookups and SMS sending stay consistent.
    """
    if raw is None:
        raise HTTPException(status_code=400, detail="Mobile number is required")

    digits = re.sub(r"\D", "", str(raw))

    # Strip the country/trunk prefix if present.
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 13 and digits.startswith("0091"):
        digits = digits[4:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid 10-digit mobile number",
        )

    return digits


@router.post("/phone")
async def set_mobile_number(
    request: dict,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Save the logged-in user's mobile number.

    Backs the blocking prompt shown to accounts that signed in with Google
    before a mobile number was mandatory. Creates the profile row if the
    account somehow has none.

    Body: {"phone": "9876543210"}
    """
    phone = normalize_mobile_number(request.get("phone"))

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    profile.phone = phone
    db.commit()
    db.refresh(profile)

    return {"phone": profile.phone}


@router.post("/google")
async def google_login(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Login with Firebase Google OAuth token.

    If user exists: Returns auth response (access_token, refresh_token, user, profile)
    If user doesn't exist: Returns {new_user: True, email, name, picture} for role selection
    """
    logger.debug("/google endpoint called, request keys: %s", request.keys())
    token = request.get("token")
    if not token:
        logger.warning("/google called without a token")
        raise HTTPException(status_code=400, detail="Token required")

    try:
        # Verify Firebase token using manual JWT verification
        decoded_token = verify_firebase_token(token)

        email = decoded_token.get("email")
        name = decoded_token.get("name", "")
        google_id = decoded_token.get("user_id") or decoded_token.get("sub")
        picture = decoded_token.get("picture", "")
        email_verified = decoded_token.get("email_verified", False)

        logger.info(
            "Google sign-in: token verified for %s (email_verified=%s)",
            email, email_verified,
        )

    except ValueError as e:
        logger.exception("Token verification ValueError")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.exception("Token verification unexpected error")
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

    # Claim gate: a signature-valid token is not enough — the identity must
    # be email-verified and come from an allowed provider, BEFORE the user
    # lookup below (rejected claims never touch the database).
    _validate_federated_claims(decoded_token)

    if not email:
        logger.warning("Google token carried no email claim")
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    # Check if user exists
    logger.debug("Google sign-in: looking up user by email %s", email)
    try:
        user = db.query(User).filter(User.user_email == email).first()
        logger.debug("Google sign-in: user found=%s", user is not None)
        if user:
            logger.debug(
                "Google sign-in: user id=%s role=%s", user.id, user.role
            )
    except Exception as e:
        logger.exception("Database query error")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    if user:
        logger.debug("Google sign-in: existing user path for %s", email)

        # 2FA parity with /login: a matched account with TOTP enrolled (or a
        # privileged account that must have it) is challenged here — BEFORE
        # any tokens are minted. Same shapes as the password path.
        _federated_totp_gate(user, request.get("otp_code"))

        try:
            # User exists - get existing profile
            profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            logger.debug("Google sign-in: profile found=%s", profile is not None)
        except Exception as e:
            logger.exception("Profile query error")
            raise HTTPException(status_code=500, detail=f"Profile query failed: {str(e)}")

        # Get instructor profile if user is instructor
        instructor_profile = None
        if user.role == "instructor":
            try:
                instructor_profile = db.query(InstructorProfile).filter(
                    InstructorProfile.user_id == user.id
                ).first()
                logger.debug(
                    "Google sign-in: instructor profile found=%s",
                    instructor_profile is not None,
                )
            except Exception as e:
                logger.exception("Instructor profile query error")
                raise HTTPException(status_code=500, detail=f"Instructor profile query failed: {str(e)}")

        try:
            # Create tokens
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": str(user.id)}, expires_delta=access_token_expires
            )
            refresh_token = create_refresh_token(data={"sub": str(user.id)})
        except Exception as e:
            logger.exception("Token creation error")
            raise HTTPException(status_code=500, detail=f"Token creation failed: {str(e)}")

        # Send login notification email for existing users AFTER the response is
        # returned. Doing this inline (await) blocks the login response on SMTP;
        # when the mail server is slow/unreachable the request hangs past the
        # client's receive timeout and Google sign-in appears to fail. Scheduling
        # it as a background task decouples login latency from email delivery.
        background_tasks.add_task(
            send_login_notification_email,
            email=user.user_email,
            user_name=user.display_name or name,
            login_method="Google",
        )

        # Update last_login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        try:
            response_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user.id,
                    "email": user.user_email,
                    "login": user.user_login,
                    "display_name": user.display_name,
                    "role": user.role,
                    "profile_completed": user.profile_completed,
                    "totp_enabled": bool(user.totp_enabled)
                },
                "profile": {
                    "id": profile.id if profile else None,
                    "user_id": profile.user_id if profile else None,
                    "first_name": profile.first_name if profile else "",
                    "last_name": profile.last_name if profile else "",
                    "phone": profile.phone if profile else "",
                    "description": profile.description if profile else "",
                    "designation": profile.designation if profile else "",
                    "address": profile.address if profile else "",
                    "city": profile.city if profile else "",
                    "state": profile.state if profile else "",
                    "country": profile.country if profile else "",
                    "postal_code": profile.postal_code if profile else "",
                    "profile_photo": profile.profile_photo if profile else "",
                    "cover_photo": profile.cover_photo if profile else "",
                    "facebook": profile.facebook if profile else "",
                    "twitter": profile.twitter if profile else "",
                    "linkedin": profile.linkedin if profile else "",
                    "website": profile.website if profile else "",
                    "show_email": profile.show_email if profile else False,
                    "receive_notifications": profile.receive_notifications if profile else True
                } if profile else None,
                "instructorProfile": {
                    "is_approved": instructor_profile.is_approved if instructor_profile else False,
                    "bio": instructor_profile.instructor_bio if instructor_profile else "",
                    "designation": instructor_profile.instructor_designation if instructor_profile else ""
                } if instructor_profile else None
            }
            return response_data
        except Exception as e:
            logger.exception("Response building error")
            raise HTTPException(status_code=500, detail=f"Response building failed: {str(e)}")
    else:
        # New user - return info for role selection
        logger.info("Google sign-in: new user %s proceeding to role selection", email)
        try:
            new_user_response = {
                "new_user": True,
                "email": email,
                "name": name,
                "picture": picture,
                "token": token  # Echo Firebase token for /complete step
            }
            return new_user_response
        except Exception as e:
            logger.exception("New user response error")
            raise HTTPException(status_code=500, detail=f"New user response failed: {str(e)}")


@router.post("/google/complete")
async def complete_google_login(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Complete Google login after user selects role.

    Creates a new user account with the selected role after receiving
    the verified Google token from the initial /google endpoint.

    Body: {
        "google_token": "<firebase_id_token>",
        "role": "student" | "instructor",
        "phone": "9876543210"
    }
    """
    token = request.get("google_token")
    role = request.get("role")

    if not token or not role:
        raise HTTPException(status_code=400, detail="Token and role are required")

    if role not in ["student", "instructor"]:
        raise HTTPException(status_code=400, detail="Role must be 'student' or 'instructor'")

    # Google gives us no phone number, so signup collects it here and it is
    # mandatory — the account is created with it rather than being chased later.
    phone = normalize_mobile_number(request.get("phone"))

    try:
        # Verify Firebase token
        decoded_token = verify_firebase_token(token)
        email = decoded_token.get("email")
        name = decoded_token.get("name", "")
        picture = decoded_token.get("picture", "")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

    # Claim gate — same rule as /google: verified email + allowed provider,
    # checked after signature verification and before any account access.
    _validate_federated_claims(decoded_token)

    # Race condition check - user may have been created meanwhile
    existing_user = db.query(User).filter(User.user_email == email).first()
    if existing_user:
        # Return existing user's auth response

        # 2FA parity: if the account that appeared in the meantime has TOTP
        # enrolled, it must clear the same challenge as /login before the
        # tokens below are minted (a brand-new account cannot have TOTP).
        _federated_totp_gate(existing_user, request.get("otp_code"))

        profile = db.query(UserProfile).filter(UserProfile.user_id == existing_user.id).first()

        # Don't lose the number the user just typed if the account was created
        # by a concurrent request (or predates the mandatory-phone rule).
        if profile and not (profile.phone or "").strip():
            profile.phone = phone
            db.commit()
            db.refresh(profile)

        instructor_profile = None
        if existing_user.role == "instructor":
            instructor_profile = db.query(InstructorProfile).filter(
                InstructorProfile.user_id == existing_user.id
            ).first()

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(existing_user.id)}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": str(existing_user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": existing_user.id,
                "email": existing_user.user_email,
                "login": existing_user.user_login,
                "display_name": existing_user.display_name,
                "role": existing_user.role,
                "profile_completed": existing_user.profile_completed
            },
            "profile": {
                "id": profile.id if profile else None,
                "user_id": profile.user_id if profile else None,
                "first_name": profile.first_name if profile else "",
                "last_name": profile.last_name if profile else "",
                "phone": profile.phone if profile else "",
                "description": profile.description if profile else "",
                "designation": profile.designation if profile else "",
                "address": profile.address if profile else "",
                "city": profile.city if profile else "",
                "state": profile.state if profile else "",
                "country": profile.country if profile else "",
                "postal_code": profile.postal_code if profile else "",
                "profile_photo": profile.profile_photo if profile else "",
                "cover_photo": profile.cover_photo if profile else "",
                "facebook": profile.facebook if profile else "",
                "twitter": profile.twitter if profile else "",
                "linkedin": profile.linkedin if profile else "",
                "website": profile.website if profile else "",
                "show_email": profile.show_email if profile else False,
                "receive_notifications": profile.receive_notifications if profile else True
            } if profile else None,
            "instructorProfile": {
                "is_approved": instructor_profile.is_approved if instructor_profile else False,
                "bio": instructor_profile.instructor_bio if instructor_profile else "",
                "designation": instructor_profile.instructor_designation if instructor_profile else ""
            } if instructor_profile else None
        }

    # Create new user with selected role
    username = email.split("@")[0] + "_" + secrets.token_hex(4)

    user = User(
        user_email=email,
        user_login=username,
        user_nicename=username,
        display_name=name,
        user_pass=secrets.token_hex(32),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create user profile with Google data
    name_parts = name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    profile = UserProfile(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        profile_photo=picture
    )
    db.add(profile)
    db.commit()

    # Create instructor profile if role is instructor
    instructor_profile = None
    if role == "instructor":
        instructor_profile = InstructorProfile(
            user_id=user.id,
            instructor_bio="",
            instructor_designation="",
            is_approved=False,  # Requires admin approval
            is_blocked=False,
            profile_completion=0
        )
        db.add(instructor_profile)
        db.commit()
        db.refresh(instructor_profile)

    # Send welcome email AFTER the response (not inline) so a slow/unreachable
    # SMTP server can't hang the signup request past the client timeout.
    from app.utils.email import send_welcome_email
    background_tasks.add_task(
        send_welcome_email,
        email=user.user_email,
        user_name=user.display_name or name,
        role=role,
    )

    # Create auth tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Update last_login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.user_email,
            "login": user.user_login,
            "display_name": user.display_name,
            "role": user.role,
            "profile_completed": user.profile_completed,
            "totp_enabled": bool(user.totp_enabled)
        },
        "profile": {
            "id": profile.id if profile else None,
            "user_id": profile.user_id if profile else None,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "phone": profile.phone if profile else "",
            "description": profile.description if profile else "",
            "designation": profile.designation if profile else "",
            "address": profile.address if profile else "",
            "city": profile.city if profile else "",
            "state": profile.state if profile else "",
            "country": profile.country if profile else "",
            "postal_code": profile.postal_code if profile else "",
            "profile_photo": profile.profile_photo if profile else "",
            "cover_photo": profile.cover_photo if profile else "",
            "facebook": profile.facebook if profile else "",
            "twitter": profile.twitter if profile else "",
            "linkedin": profile.linkedin if profile else "",
            "website": profile.website if profile else "",
            "show_email": profile.show_email if profile else False,
            "receive_notifications": profile.receive_notifications if profile else True
        } if profile else None,
        "instructorProfile": {
            "is_approved": instructor_profile.is_approved if instructor_profile else False,
            "bio": instructor_profile.instructor_bio if instructor_profile else "",
            "designation": instructor_profile.instructor_designation if instructor_profile else ""
        } if instructor_profile else None
    }

@router.post("/linkedin")
async def linkedin_login(
    payload: dict,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Exchange LinkedIn auth code for user profile and login"""
    import httpx as httpx_client
    import os

    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code required")

    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    redirect_uri = "https://lms.sashainfinity.com/auth/linkedin/callback"

    try:
        async with httpx_client.AsyncClient(timeout=10.0) as client:
            # Exchange code for access token
            token_res = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if token_res.status_code != 200:
                raise HTTPException(status_code=401, detail="Failed to get LinkedIn token")
            token_data = token_res.json()
            li_access_token = token_data.get("access_token")

            # Get user profile using OpenID Connect userinfo
            profile_res = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {li_access_token}"}
            )
            if profile_res.status_code != 200:
                raise HTTPException(status_code=401, detail="Failed to get LinkedIn profile")
            profile = profile_res.json()

    except httpx_client.RequestError as e:
        raise HTTPException(status_code=500, detail=f"LinkedIn request failed: {str(e)}")

    email = profile.get("email")
    name = profile.get("name", "")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by LinkedIn")

    # Find or create user
    user = db.query(User).filter(User.user_email == email).first()
    if not user:
        import secrets
        username = email.split("@")[0] + "_" + secrets.token_hex(4)
        user = User(
            user_email=email,
            user_login=username,
            user_nicename=username,
            display_name=name,
            user_pass=secrets.token_hex(32),
            role="student",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    _set_shared_session(response, http_request, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "user_email": user.user_email,
            "display_name": user.display_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    }
