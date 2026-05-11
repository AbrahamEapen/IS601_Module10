# tests/unit/test_hashing.py
"""Unit tests for the module-level hash_password and verify_password functions."""

import pytest
from app.models.user import hash_password, verify_password


def test_hash_password_returns_string():
    """hash_password should return a non-empty string."""
    result = hash_password("SecurePass1")
    assert isinstance(result, str)
    assert len(result) > 0


def test_hash_password_is_not_plain_text():
    """The hash must differ from the original password."""
    plain = "SecurePass1"
    assert hash_password(plain) != plain


def test_hash_password_is_deterministically_different():
    """bcrypt generates a unique salt each call, so two hashes of the same
    password must NOT be equal."""
    h1 = hash_password("SecurePass1")
    h2 = hash_password("SecurePass1")
    assert h1 != h2


def test_verify_password_correct():
    """verify_password returns True for the correct plain-text password."""
    plain = "SecurePass1"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    """verify_password returns False for an incorrect password."""
    hashed = hash_password("SecurePass1")
    assert verify_password("WrongPass1", hashed) is False


def test_verify_password_empty_plain():
    """verify_password returns False when given an empty string."""
    hashed = hash_password("SecurePass1")
    assert verify_password("", hashed) is False


@pytest.mark.parametrize("plain", [
    "Abcdef1",           # minimum valid
    "A" * 50 + "a1",    # long password
    "P@ssw0rd!",        # special characters
    "TéstPass1",        # unicode
])
def test_hash_and_verify_roundtrip(plain):
    """hash then verify must always succeed for the same password."""
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
