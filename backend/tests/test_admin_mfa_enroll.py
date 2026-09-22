import pytest
import pyotp
from admin_mfa_enroll import enroll


def test_admin_enrollment_requires_a_working_code_and_cannot_reset(db, make_user):
    user = make_user(role="admin")
    secret = pyotp.random_base32()
    with pytest.raises(ValueError):
        enroll(db, user, secret, "invalid")
    assert not user.totp_enabled
    enroll(db, user, secret, pyotp.TOTP(secret).now())
    assert user.totp_enabled and user.totp_secret == secret
    with pytest.raises(ValueError):
        enroll(db, user, pyotp.random_base32(), "invalid")
    assert user.totp_secret == secret


def test_enrollment_does_not_elevate_students(db, make_user):
    user = make_user(role="student")
    secret = pyotp.random_base32()
    with pytest.raises(ValueError):
        enroll(db, user, secret, pyotp.TOTP(secret).now())
    assert user.role == "student" and not user.totp_enabled
