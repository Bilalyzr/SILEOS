"""
Authentication Service - Business logic for user authentication
"""

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional

from app.core.database import get_db
from app.core.security import verify_password, verify_token, is_token_revoked, is_session_revoked
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

class AuthService:
    """Authentication service class"""

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with email and password
        Returns (user, error_message) tuple
        - If successful: (User, None)
        - If email not found: (None, "email_not_found")
        - If password wrong: (None, "incorrect_password")
        - If instructor not approved: (None, "instructor_not_approved")
        """
        from app.models.user import InstructorProfile

        user = db.query(User).filter(User.user_email == email).first()
        if not user:
            return None, "email_not_found"
        if not verify_password(password, user.user_pass):
            return None, "incorrect_password"

        # Check if instructor is approved
        if user.role == "instructor":
            instructor_profile = db.query(InstructorProfile).filter(
                InstructorProfile.user_id == user.id
            ).first()

            # If no instructor profile exists, or if not approved, block login
            if not instructor_profile:
                return None, "instructor_not_approved"

            if not instructor_profile.is_approved:
                return None, "instructor_not_approved"

        return user, None

    @staticmethod
    def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
        request: Request = None,
    ) -> User:
        """
        Get current authenticated user from JWT token
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            # Accept normal access tokens AND short-lived admin-impersonation
            # tokens. Refresh / password-reset / email-verification tokens
            # are still rejected.
            payload = verify_token(
                token,
                expected_type=["access", "impersonation_access"],
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        # Logout denylist: a token the user explicitly logged out of must
        # not keep working until natural expiry.
        if is_token_revoked(token):
            raise credentials_exception

        # Global logout: tokens minted before the user's last logout (on ANY
        # origin — sibling subdomains keep their own localStorage sessions)
        # are dead everywhere.
        if is_session_revoked(payload):
            raise credentials_exception

        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception

        if request is not None:
            request.state.actor_role = user.role
            user._request_state = request.state

        # Attach request-scoped impersonation provenance so downstream
        # guards can refuse chained impersonation. None for plain access
        # tokens; admin id for impersonation tokens.
        try:
            token_type = payload.get("type")
            impersonated_by = payload.get("impersonated_by") if token_type == "impersonation_access" else None
            user._impersonated_by = impersonated_by
        except Exception:
            # Dynamic attr assignment shouldn't ever fail on a SQLAlchemy
            # instance, but we don't want a request to die on it.
            import logging
            logging.getLogger(__name__).exception("Failed to set _impersonated_by attribute")

        return user

    @staticmethod
    def get_optional_current_user(
        token: Optional[str] = Depends(optional_oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> Optional[User]:
        """
        Get current user if authenticated, None otherwise (for optional auth)
        """
        if not token:
            return None

        try:
            payload = verify_token(token)
            user_id: str = payload.get("sub")
            if user_id is None:
                return None

            # Logout denylist (see get_current_user): a revoked token is
            # treated as anonymous here, not as an error.
            if is_token_revoked(token):
                return None

            # Global logout (see get_current_user).
            if is_session_revoked(payload):
                return None

            user = db.query(User).filter(User.id == int(user_id)).first()
            return user
        except JWTError:
            return None

    @staticmethod
    def get_current_active_user(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Get current active user (status must be active)
        """
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return current_user

    @staticmethod
    def require_role(allowed_roles: list):
        """
        Decorator to require specific roles
        """
        def role_checker(current_user: User = Depends(AuthService.get_current_active_user)):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return current_user
        return role_checker

    @staticmethod
    def require_instructor(current_user: User = Depends(get_current_active_user)) -> User:
        """
        Require instructor role
        """
        if current_user.role not in ["instructor", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor access required"
            )
        return current_user

    @staticmethod
    def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
        """
        Require admin role. SuperAdmin is a superset of admin — it inherits
        every admin endpoint — so a superadmin satisfies this guard too.
        """
        if current_user.role not in ("admin", "superadmin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

    @staticmethod
    def require_superadmin(current_user: User = Depends(get_current_active_user)) -> User:
        """
        Require superadmin role. This is the only guard SuperAdmin does NOT
        share with admin — monitoring dashboards & cross-admin impersonation
        are superadmin-exclusive.
        """
        if current_user.role != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SuperAdmin access required"
            )
        return current_user

    @staticmethod
    def require_spoc(current_user: User = Depends(get_current_active_user)) -> User:
        """Require SPOC (Single Point of Contact for a college cohort)."""
        if current_user.role != "spoc":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SPOC access required"
            )
        return current_user

    @staticmethod
    def require_spoc_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
        """SPOC or admin — admin can act on any cohort; SPOC on their own."""
        if current_user.role not in ("spoc", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SPOC or admin access required"
            )
        return current_user

    @staticmethod
    def require_company(current_user: User = Depends(get_current_active_user)) -> User:
        """Require company role. Does NOT check is_approved — the companies
        router itself must additionally gate browse/interest endpoints on
        the Company.is_approved flag."""
        if current_user.role != "company":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company access required"
            )
        return current_user

    @staticmethod
    def require_company_or_manager(current_user: User = Depends(get_current_active_user)) -> User:
        """Allow company owners, their managers, and admins."""
        if current_user.role not in ("company", "company_manager", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company access required"
            )
        return current_user

    @staticmethod
    def require_company_owner(current_user: User = Depends(get_current_active_user)) -> User:
        """Require company owner role (not managers)."""
        if current_user.role != "company":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company owner access required"
            )
        return current_user
