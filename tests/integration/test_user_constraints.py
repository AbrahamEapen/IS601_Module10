# tests/integration/test_user_constraints.py
"""Integration tests for user uniqueness constraints and email validation.

These tests require a real PostgreSQL database (provided by the db_session
fixture in conftest.py, which is wired to the Postgres container in CI).
"""

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.base import UserCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(db, username, email, password="TestPass1"):
    User.register(db, {"username": username, "email": email, "password": password})
    db.commit()


# ---------------------------------------------------------------------------
# Email uniqueness (via User.register — catches duplicates before DB flush)
# ---------------------------------------------------------------------------

class TestEmailUniqueness:
    def test_duplicate_email_raises_value_error(self, db_session):
        """register() raises ValueError when the same email is used twice."""
        _register(db_session, "user_a", "shared@example.com")
        with pytest.raises(ValueError, match="Username or email already exists"):
            _register(db_session, "user_b", "shared@example.com")

    def test_same_email_different_case_is_distinct(self, db_session):
        """Postgres treats 'A@X.com' and 'a@x.com' as different strings by default."""
        _register(db_session, "user_c", "Case@example.com")
        # lower-case variant should succeed (no uniqueness violation at DB level)
        _register(db_session, "user_d", "case@example.com")
        count = db_session.query(User).filter(
            User.email.in_(["Case@example.com", "case@example.com"])
        ).count()
        assert count == 2

    def test_direct_db_duplicate_email_raises_integrity_error(self, db_session):
        """Inserting a duplicate email directly raises IntegrityError at DB level."""
        u1 = User(email="dupe@example.com", username="u1x", password_hash="h")
        db_session.add(u1)
        db_session.commit()

        u2 = User(email="dupe@example.com", username="u2x", password_hash="h")
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


# ---------------------------------------------------------------------------
# Username uniqueness
# ---------------------------------------------------------------------------

class TestUsernameUniqueness:
    def test_duplicate_username_raises_value_error(self, db_session):
        """register() raises ValueError when the same username is used twice."""
        _register(db_session, "sharedname", "first@example.com")
        with pytest.raises(ValueError, match="Username or email already exists"):
            _register(db_session, "sharedname", "second@example.com")

    def test_direct_db_duplicate_username_raises_integrity_error(self, db_session):
        """Inserting a duplicate username directly raises IntegrityError."""
        u1 = User(email="u1_unique@example.com", username="dupename", password_hash="h")
        db_session.add(u1)
        db_session.commit()

        u2 = User(email="u2_unique@example.com", username="dupename", password_hash="h")
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


# ---------------------------------------------------------------------------
# Email format validation (via Pydantic — no DB required, but kept here as
# integration-level checks to confirm the schema gate before any DB write)
# ---------------------------------------------------------------------------

class TestEmailValidation:
    @pytest.mark.parametrize("bad_email", [
        "plainaddress",
        "missing@",
        "@nodomain.com",
        "two@@signs.com",
        "spaces in@email.com",
        "",
    ])
    def test_invalid_email_rejected_by_schema(self, bad_email):
        """UserCreate must reject malformed email strings."""
        with pytest.raises(ValidationError):
            UserCreate(username="validuser", email=bad_email, password="TestPass1")

    @pytest.mark.parametrize("good_email", [
        "user@example.com",
        "user+tag@sub.domain.org",
        "firstname.lastname@company.io",
    ])
    def test_valid_email_accepted_by_schema(self, good_email):
        """UserCreate must accept well-formed email strings."""
        uc = UserCreate(username="validuser", email=good_email, password="TestPass1")
        assert uc.email == good_email

    def test_register_with_invalid_email_raises(self, db_session):
        """User.register() must propagate a ValueError for an invalid email."""
        with pytest.raises((ValueError, ValidationError)):
            User.register(
                db_session,
                {"username": "validuser", "email": "not-an-email", "password": "TestPass1"},
            )


# ---------------------------------------------------------------------------
# Original user persists after constraint failure
# ---------------------------------------------------------------------------

class TestPersistenceAfterConstraintViolation:
    def test_original_user_survives_duplicate_attempt(self, db_session):
        """After a failed duplicate-email insert, the original user is untouched."""
        _register(db_session, "survivor", "survive@example.com")
        original = db_session.query(User).filter_by(email="survive@example.com").first()
        assert original is not None

        with pytest.raises(ValueError):
            _register(db_session, "attacker", "survive@example.com")

        still_there = db_session.query(User).filter_by(email="survive@example.com").first()
        assert still_there is not None
        assert still_there.id == original.id
