"""Offline first-enrolment for an existing administrator; run in a trusted terminal.

Does not create accounts, change roles/passwords or reset enrolled MFA.
Do not pipe the provisioning secret into shared logs.
"""
import argparse
from getpass import getpass
import pyotp
from app import models  # noqa: F401
from app.core.database import SessionLocal
from app.models.user import User


def enroll(db, user, secret, code):
    if user.role not in {"admin", "superadmin"} or not user.is_active:
        raise ValueError("An active existing administrator is required")
    if user.totp_enabled:
        raise ValueError("MFA is already enrolled; this command cannot reset it")
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        raise ValueError("Authenticator code did not verify; no changes saved")
    user.totp_secret, user.totp_enabled = secret, True
    db.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.query(User).filter_by(user_email=args.email).one_or_none()
        if user is None or user.role not in {"admin", "superadmin"} or not user.is_active:
            parser.error("No active administrator with that email")
        if user.totp_enabled:
            parser.error("MFA is already enrolled; no changes made")
        secret = pyotp.random_base32()
        print("Add this setup key to your authenticator in a private terminal:")
        print(secret)
        try:
            enroll(db, user, secret, getpass("Current six-digit authenticator code: ").strip())
        except ValueError as exc:
            parser.error(str(exc))
        print("Administrator MFA enrolled and verified. Use password plus your current authenticator code to sign in.")


if __name__ == "__main__":
    main()
