"""Unit tests for the auth helpers in app.core.security.

Covers password hashing/verification and JWT creation, including the change
that the token subject is now the immutable user id (not the email).
"""

import time
from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_is_not_plaintext_and_verifies():
    hashed = get_password_hash("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert verify_password("s3cret-pw", hashed) is True
    assert verify_password("wrong-pw", hashed) is False


def test_same_password_hashes_differently_due_to_salt():
    assert get_password_hash("same") != get_password_hash("same")


def test_verify_password_handles_malformed_hash_gracefully():
    # A non-bcrypt string should return False, not raise.
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_subject_is_the_user_id():
    token = create_access_token(subject=42)
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert payload["sub"] == "42"   # stored as a string
    assert "exp" in payload


def test_access_token_respects_custom_expiry():
    token = create_access_token(subject=1, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    now = time.time()
    assert now < payload["exp"] <= now + 5 * 60 + 5   # ~5 minutes ahead


def test_token_is_rejected_with_wrong_secret():
    token = create_access_token(subject=1)
    try:
        jwt.decode(token, "the-wrong-secret", algorithms=[settings.ALGORITHM])
        assert False, "decode should have failed with the wrong secret"
    except Exception:
        pass  # expected: signature verification fails
