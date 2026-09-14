"""
Enhanced Authentication Security for SashaInfinity LMS
Provides advanced authentication features like brute force protection,
session management, and account lockout
"""

import redis
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
from app.core.database import get_db
from app.models.user import User
from app.core.security_middleware import log_security_event, security_logger
from app.core.config import get_settings
import secrets
import hashlib

settings = get_settings()

class BruteForceProtection:
    """Brute force attack protection"""

    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def record_failed_attempt(self, email: str, ip_address: str):
        """Record a failed login attempt"""
        email_key = f"failed_attempts:email:{email}"
        ip_key = f"failed_attempts:ip:{ip_address}"

        try:
            pipe = self.redis_client.pipeline()

            # Increment email counter
            pipe.incr(email_key)
            pipe.expire(email_key, 3600)  # 1 hour window

            # Increment IP counter
            pipe.incr(ip_key)
            pipe.expire(ip_key, 3600)  # 1 hour window

            results = pipe.execute()

            email_attempts = int(results[0])
            ip_attempts = int(results[2])

            # Log suspicious activity
            if email_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                await log_security_event(
                    "BRUTE_FORCE_EMAIL_LIMIT",
                    client_ip=ip_address,
                    details={"email": email, "attempts": email_attempts}
                )

            if ip_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                await log_security_event(
                    "BRUTE_FORCE_IP_LIMIT",
                    client_ip=ip_address,
                    details={"attempts": ip_attempts}
                )

            return email_attempts, ip_attempts

        except Exception as e:
            security_logger.error(f"Error recording failed attempt: {e}")
            return 0, 0

    async def is_account_locked(self, email: str) -> Tuple[bool, int]:
        """Check if account is locked and return remaining lock time in minutes"""
        lock_key = f"account_locked:{email}"

        try:
            ttl = self.redis_client.ttl(lock_key)
            if ttl > 0:
                return True, ttl // 60  # Convert to minutes
            return False, 0
        except Exception as e:
            security_logger.error(f"Error checking account lock: {e}")
            return False, 0

    async def lock_account(self, email: str, duration_minutes: int = None):
        """Lock account for specified duration"""
        lock_key = f"account_locked:{email}"
        duration = duration_minutes or settings.LOCKOUT_DURATION_MINUTES

        try:
            self.redis_client.setex(lock_key, duration * 60, "locked")
            await log_security_event(
                "ACCOUNT_LOCKED",
                details={"email": email, "duration_minutes": duration}
            )
        except Exception as e:
            security_logger.error(f"Error locking account: {e}")

    async def clear_failed_attempts(self, email: str):
        """Clear failed attempts after successful login"""
        email_key = f"failed_attempts:email:{email}"

        try:
            self.redis_client.delete(email_key)
        except Exception as e:
            security_logger.error(f"Error clearing failed attempts: {e}")

class SessionManager:
    """Advanced session management"""

    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def create_session(self, user_id: int, ip_address: str, user_agent: str) -> str:
        """Create new session"""
        session_id = secrets.token_urlsafe(32)
        session_key = f"session:{session_id}"

        session_data = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent[:200],  # Limit length
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "is_active": True
        }

        try:
            # Store session data
            self.redis_client.hset(session_key, mapping=session_data)
            self.redis_client.expire(session_key, settings.SESSION_TIMEOUT_MINUTES * 60)

            # Track user sessions
            user_sessions_key = f"user_sessions:{user_id}"
            self.redis_client.sadd(user_sessions_key, session_id)
            self.redis_client.expire(user_sessions_key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

            # Check session limit
            await self._enforce_session_limit(user_id)

            await log_security_event(
                "SESSION_CREATED",
                user_id=user_id,
                client_ip=ip_address,
                details={"session_id": session_id[:16]}  # Log only partial session ID
            )

            return session_id

        except Exception as e:
            security_logger.error(f"Error creating session: {e}")
            return None

    async def validate_session(self, session_id: str, ip_address: str) -> Optional[Dict]:
        """Validate session and update activity"""
        session_key = f"session:{session_id}"

        try:
            # Check if session exists
            if not self.redis_client.exists(session_key):
                return None

            # Get session data
            session_data = self.redis_client.hgetall(session_key)

            if not session_data or not session_data.get("is_active", "False"):
                return None

            # Validate IP address (optional - can be disabled for mobile users)
            original_ip = session_data.get("ip_address", "")
            if original_ip and original_ip != ip_address:
                security_logger.warning(
                    f"Session IP mismatch: {original_ip} vs {ip_address} for user {session_data.get('user_id')}"
                )
                await log_security_event(
                    "SESSION_IP_MISMATCH",
                    user_id=int(session_data.get("user_id", 0)),
                    client_ip=ip_address,
                    details={"original_ip": original_ip, "session_id": session_id[:16]}
                )
                # Don't invalidate immediately, but log for monitoring

            # Update last activity
            self.redis_client.hset(session_key, "last_activity", datetime.utcnow().isoformat())

            # Extend session expiration
            self.redis_client.expire(session_key, settings.SESSION_TIMEOUT_MINUTES * 60)

            return session_data

        except Exception as e:
            security_logger.error(f"Error validating session: {e}")
            return None

    async def invalidate_session(self, session_id: str, reason: str = "logout"):
        """Invalidate specific session"""
        session_key = f"session:{session_id}"

        try:
            session_data = self.redis_client.hgetall(session_key)
            user_id = session_data.get("user_id") if session_data else None

            # Remove session
            self.redis_client.delete(session_key)

            # Remove from user sessions set
            if user_id:
                user_sessions_key = f"user_sessions:{user_id}"
                self.redis_client.srem(user_sessions_key, session_id)

            await log_security_event(
                "SESSION_INVALIDATED",
                user_id=int(user_id) if user_id else None,
                details={"reason": reason, "session_id": session_id[:16]}
            )

        except Exception as e:
            security_logger.error(f"Error invalidating session: {e}")

    async def invalidate_user_sessions(self, user_id: int, current_session_id: str = None):
        """Invalidate all sessions for a user except current"""
        user_sessions_key = f"user_sessions:{user_id}"

        try:
            session_ids = self.redis_client.smembers(user_sessions_key)

            for session_id in session_ids:
                if session_id != current_session_id:
                    await self.invalidate_session(session_id, "session_limit")

            await log_security_event(
                "USER_SESSIONS_INVALIDATED",
                user_id=user_id,
                details={"session_count": len(session_ids)}
            )

        except Exception as e:
            security_logger.error(f"Error invalidating user sessions: {e}")

    async def _enforce_session_limit(self, user_id: int):
        """Enforce maximum concurrent sessions"""
        user_sessions_key = f"user_sessions:{user_id}"

        try:
            session_ids = self.redis_client.smembers(user_sessions_key)
            active_sessions = []

            # Check which sessions are still active
            for session_id in session_ids:
                session_key = f"session:{session_id}"
                if self.redis_client.exists(session_key):
                    active_sessions.append(session_id)

            # If too many sessions, invalidate oldest
            if len(active_sessions) > settings.MAX_CONCURRENT_SESSIONS:
                # Sort by creation time and invalidate oldest
                sessions_with_time = []
                for session_id in active_sessions:
                    session_key = f"session:{session_id}"
                    created_at = self.redis_client.hget(session_key, "created_at")
                    sessions_with_time.append((created_at, session_id))

                sessions_with_time.sort()
                excess_sessions = sessions_with_time[:-settings.MAX_CONCURRENT_SESSIONS]

                for _, session_id in excess_sessions:
                    await self.invalidate_session(session_id, "session_limit")

        except Exception as e:
            security_logger.error(f"Error enforcing session limit: {e}")

class PasswordSecurity:
    """Enhanced password security features"""

    @staticmethod
    async def check_password_history(user_id: int, new_password: str, db: Session) -> Tuple[bool, str]:
        """Check if password was used before (prevent password reuse)"""
        # This would require storing password history
        # For now, implement basic checks
        from app.core.security import get_password_hash

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        # Check against current password
        from app.core.security import verify_password
        if verify_password(new_password, user.user_pass):
            return False, "Cannot reuse current password"

        # TODO: Check against password history
        return True, "Password is not in history"

    @staticmethod
    async def enforce_password_change_frequency(user: User, db: Session) -> Tuple[bool, int]:
        """Check if password needs to be changed"""
        if not user.last_login:
            return True, settings.PASSWORD_CHANGE_FREQUENCY_DAYS

        days_since_last_change = (datetime.utcnow() - user.last_login).days

        if days_since_last_change >= settings.PASSWORD_CHANGE_FREQUENCY_DAYS:
            return True, days_since_last_change

        return False, days_since_last_change

    @staticmethod
    def generate_password_reset_token(user_id: int) -> str:
        """Generate secure password reset token"""
        token_data = f"{user_id}:{datetime.utcnow().timestamp()}:{secrets.token_urlsafe(32)}"
        return hashlib.sha256(token_data.encode()).hexdigest()

# Initialize security components
brute_force_protection = BruteForceProtection()
session_manager = SessionManager()
password_security = PasswordSecurity()

async def authenticate_user_with_security(db: Session, email: str, password: str, ip_address: str) -> Tuple[Optional[User], Optional[str]]:
    """Enhanced user authentication with security features"""

    # Check if account is locked
    is_locked, lock_time = await brute_force_protection.is_account_locked(email)
    if is_locked:
        await log_security_event(
            "LOGIN_ATTEMPT_ON_LOCKED_ACCOUNT",
            client_ip=ip_address,
            details={"email": email, "lock_time_minutes": lock_time}
        )
        return None, "account_locked"

    # Check brute force limits
    email_attempts, ip_attempts = await brute_force_protection.record_failed_attempt(email, ip_address)

    if email_attempts >= settings.MAX_LOGIN_ATTEMPTS or ip_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        await brute_force_protection.lock_account(email)
        return None, "account_locked_due_to_attempts"

    # Standard authentication
    from app.services.auth_service import AuthService
    user, auth_error = AuthService.authenticate_user(db, email, password)

    if not user:
        # Authentication failed
        await log_security_event(
            "FAILED_LOGIN",
            user_id=user.id if user else None,
            client_ip=ip_address,
            details={"email": email, "error": auth_error}
        )
        return None, auth_error

    # Authentication successful
    await brute_force_protection.clear_failed_attempts(email)

    # Update user login info
    user.last_login = datetime.utcnow()
    db.commit()

    # Create session
    session_id = await session_manager.create_session(
        user.id,
        ip_address,
        "default"  # This should come from request headers
    )

    await log_security_event(
        "SUCCESSFUL_LOGIN",
        user_id=user.id,
        client_ip=ip_address,
        details={"email": email}
    )

    return user, None

async def logout_user_with_security(user_id: int, session_id: str, ip_address: str):
    """Enhanced logout with security features"""
    await session_manager.invalidate_session(session_id, "logout")

    await log_security_event(
        "USER_LOGOUT",
        user_id=user_id,
        client_ip=ip_address,
        details={"session_id": session_id[:16]}
    )

async def validate_token_with_security(token: str, ip_address: str) -> Optional[Dict]:
    """Enhanced token validation with security checks"""
    try:
        from jose import jwt, JWTError
        from app.core.config import get_settings
        settings = get_settings()

        # Decode JWT token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            return None

        # This is a simplified validation
        # In production, you might want to check against session storage
        return {"user_id": int(user_id), "is_valid": True}

    except JWTError as e:
        await log_security_event(
            "INVALID_TOKEN",
            client_ip=ip_address,
            details={"error": str(e)}
        )
        return None

# Password complexity requirements
PASSWORD_COMPLEXITY_RULES = {
    "min_length": 12,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_numbers": True,
    "require_special_chars": True,
    "forbidden_patterns": ["password", "123456", "qwerty", "admin"],
    "max_repeated_chars": 2,
}