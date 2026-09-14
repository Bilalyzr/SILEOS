"""Legacy password-hash login (2026-09-01).

Users migrated from the WordPress main site carry non-bcrypt ``user_pass``
hashes. Login must verify them in-memory (read-only: no DB writes) so
main-site users can sign in with their original password:

* ``$2b$`` / ``$2a$`` / ``$2y$`` bcrypt            — native format
* ``$wp$2y$...`` (WordPress bcrypt w/ ``$wp$``)    — strip prefix, bcrypt
* ``$P$...`` phpass (classic WordPress)            — passlib phpass
* 64-char hex sha256 (unsalted legacy import)      — hashlib compare

Wrong passwords and malformed hashes must return False, never raise
(today ``pwd_context.verify`` raises ``UnknownHashError`` on legacy
formats, turning login into a 500).
"""

import hashlib

import pytest
from passlib.context import CryptContext

from app.core.security import verify_password

PASSWORD = "Secret123!"
OTHER = "WrongPass999!"

bcrypt_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="module")
def hashes():
    plain_bcrypt = bcrypt_ctx.hash(PASSWORD)
    return {
        "bcrypt": plain_bcrypt,
        "wp_bcrypt": "$wp$" + plain_bcrypt,
        "phpass": __import__("passlib.hash", fromlist=["phpass"]).phpass.hash(PASSWORD),
        "sha256_hex": hashlib.sha256(PASSWORD.encode()).hexdigest(),
    }


@pytest.mark.parametrize("format", ["bcrypt", "wp_bcrypt", "phpass", "sha256_hex"])
def test_correct_password_verifies(format, hashes):
    assert verify_password(PASSWORD, hashes[format]) is True


@pytest.mark.parametrize("format", ["bcrypt", "wp_bcrypt", "phpass", "sha256_hex"])
def test_wrong_password_rejects(format, hashes):
    assert verify_password(OTHER, hashes[format]) is False


def test_malformed_hash_returns_false_not_raise():
    assert verify_password(PASSWORD, "not-a-real-hash") is False


def test_empty_hash_returns_false_not_raise():
    assert verify_password(PASSWORD, "") is False
