# tests/unit/test_user_schemas.py
"""Unit tests for UserCreate and UserRead Pydantic schemas."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.schemas.base import UserCreate
from app.schemas.user import UserRead


# ---------------------------------------------------------------------------
# UserCreate
# ---------------------------------------------------------------------------

class TestUserCreate:
    def test_valid_minimal_input(self):
        """UserCreate accepts the three required fields."""
        uc = UserCreate(username="alice42", email="alice@example.com", password="Abcdef1")
        assert uc.username == "alice42"
        assert uc.email == "alice@example.com"
        assert uc.password == "Abcdef1"

    def test_extra_fields_are_ignored(self):
        """Extra fields (e.g. first_name, last_name) are silently dropped."""
        uc = UserCreate(
            username="alice42",
            email="alice@example.com",
            password="Abcdef1",
            first_name="Alice",
            last_name="Smith",
        )
        assert not hasattr(uc, "first_name")

    def test_invalid_email_raises(self):
        """Non-email string must fail validation."""
        with pytest.raises(ValidationError):
            UserCreate(username="alice42", email="not-an-email", password="Abcdef1")

    def test_username_too_short_raises(self):
        """Username shorter than 3 chars must fail."""
        with pytest.raises(ValidationError):
            UserCreate(username="ab", email="alice@example.com", password="Abcdef1")

    def test_username_too_long_raises(self):
        """Username longer than 50 chars must fail."""
        with pytest.raises(ValidationError):
            UserCreate(username="a" * 51, email="alice@example.com", password="Abcdef1")

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(username="alice42", email="alice@example.com", password="Ab1")

    def test_password_no_uppercase_raises(self):
        with pytest.raises(ValidationError, match="uppercase"):
            UserCreate(username="alice42", email="alice@example.com", password="abcdef1")

    def test_password_no_lowercase_raises(self):
        with pytest.raises(ValidationError, match="lowercase"):
            UserCreate(username="alice42", email="alice@example.com", password="ABCDEF1")

    def test_password_no_digit_raises(self):
        with pytest.raises(ValidationError, match="digit"):
            UserCreate(username="alice42", email="alice@example.com", password="AbcdefGH")

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(email="alice@example.com", password="Abcdef1")

    def test_missing_email_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(username="alice42", password="Abcdef1")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(username="alice42", email="alice@example.com")


# ---------------------------------------------------------------------------
# UserRead
# ---------------------------------------------------------------------------

class TestUserRead:
    def _make(self, **overrides):
        defaults = dict(
            username="alice42",
            email="alice@example.com",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        defaults.update(overrides)
        return UserRead(**defaults)

    def test_valid_data(self):
        """UserRead builds correctly from valid fields."""
        ur = self._make()
        assert ur.username == "alice42"
        assert ur.email == "alice@example.com"
        assert isinstance(ur.created_at, datetime)

    def test_no_password_hash_field(self):
        """UserRead must not expose a password_hash attribute."""
        ur = self._make()
        assert not hasattr(ur, "password_hash")
        assert not hasattr(ur, "password")

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            self._make(email="bad-email")

    def test_from_orm_attributes(self):
        """UserRead.model_validate works with object-like sources (from_attributes=True)."""
        class FakeUser:
            username = "bob"
            email = "bob@example.com"
            created_at = datetime(2025, 6, 1)

        ur = UserRead.model_validate(FakeUser())
        assert ur.username == "bob"
