# ======================================================================================
# tests/integration/test_user.py
# ======================================================================================

import pytest
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from tests.conftest import create_fake_user, managed_db_session

logger = logging.getLogger(__name__)

# ======================================================================================
# Basic Connection & Session Tests
# ======================================================================================

def test_database_connection(db_session):
    """Verify that the database connection is working."""
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    logger.info("Database connection test passed")


def test_managed_session():
    """Test the managed_db_session context manager for one-off queries and rollbacks."""
    with managed_db_session() as session:
        session.execute(text("SELECT 1"))
        try:
            session.execute(text("SELECT * FROM nonexistent_table"))
        except Exception as e:
            assert "nonexistent_table" in str(e)

# ======================================================================================
# Session Handling & Partial Commits
# ======================================================================================

def test_session_handling(db_session):
    """
    Demonstrate partial commits:
      - user1 is committed
      - user2 fails (duplicate email), triggers rollback, user1 remains
      - user3 is committed
      - final check ensures we only have user1 and user3
    """
    initial_count = db_session.query(User).count()
    assert initial_count == 0, f"Expected 0 users before test, found {initial_count}"

    user1 = User(
        first_name="Test",
        last_name="User",
        email="test1@example.com",
        username="testuser1",
        password_hash="hashed_password123",
    )
    db_session.add(user1)
    db_session.commit()

    assert db_session.query(User).count() == 1

    try:
        user2 = User(
            first_name="Test",
            last_name="User",
            email="test1@example.com",  # Duplicate
            username="testuser2",
            password_hash="hashed_password456",
        )
        db_session.add(user2)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()

    found_user1 = db_session.query(User).filter_by(email="test1@example.com").first()
    assert found_user1 is not None
    assert found_user1.username == "testuser1"

    user3 = User(
        first_name="Test",
        last_name="User",
        email="test3@example.com",
        username="testuser3",
        password_hash="hashed_password789",
    )
    db_session.add(user3)
    db_session.commit()

    users = db_session.query(User).order_by(User.email).all()
    emails = {user.email for user in users}
    assert len(users) == 2
    assert "test1@example.com" in emails
    assert "test3@example.com" in emails


# ======================================================================================
# User Creation Tests
# ======================================================================================

def test_create_user_with_faker(db_session):
    """Create a single user using Faker-generated data and verify it was saved."""
    user_data = create_fake_user()

    user = User(
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        email=user_data["email"],
        username=user_data["username"],
        password_hash=User.hash_password(user_data["password"]),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == user_data["email"]
    logger.info(f"Successfully created user with ID: {user.id}")


def test_create_multiple_users(db_session):
    """Create multiple users in a loop and verify they are all saved."""
    users = []
    for _ in range(3):
        user_data = create_fake_user()
        user = User(
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            email=user_data["email"],
            username=user_data["username"],
            password_hash=User.hash_password(user_data["password"]),
        )
        users.append(user)
        db_session.add(user)

    db_session.commit()
    assert len(users) == 3

# ======================================================================================
# Query Tests
# ======================================================================================

def test_query_methods(db_session, seed_users):
    """Illustrate various query methods using seeded users."""
    user_count = db_session.query(User).count()
    assert user_count >= len(seed_users)

    first_user = seed_users[0]
    found = db_session.query(User).filter_by(email=first_user.email).first()
    assert found is not None

    users_by_email = db_session.query(User).order_by(User.email).all()
    assert len(users_by_email) >= len(seed_users)

# ======================================================================================
# Transaction / Rollback Tests
# ======================================================================================

def test_transaction_rollback(db_session):
    """Demonstrate how a partial transaction fails and triggers rollback."""
    initial_count = db_session.query(User).count()

    try:
        user_data = create_fake_user()
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            password_hash=User.hash_password(user_data["password"]),
        )
        db_session.add(user)
        db_session.execute(text("SELECT * FROM nonexistent_table"))
        db_session.commit()
    except Exception:
        db_session.rollback()

    final_count = db_session.query(User).count()
    assert final_count == initial_count

# ======================================================================================
# Update Tests
# ======================================================================================

def test_update_with_refresh(db_session, test_user):
    """Update a user's email and refresh the session to see updated fields."""
    original_email = test_user.email
    original_update_time = test_user.updated_at

    new_email = f"new_{original_email}"
    test_user.email = new_email
    db_session.commit()
    db_session.refresh(test_user)

    assert test_user.email == new_email
    assert test_user.updated_at > original_update_time

# ======================================================================================
# Bulk Operation Tests
# ======================================================================================

@pytest.mark.slow
def test_bulk_operations(db_session):
    """Test bulk inserting multiple users at once (marked slow)."""
    users_data = [create_fake_user() for _ in range(10)]
    users = [
        User(
            email=d["email"],
            username=d["username"],
            password_hash=User.hash_password(d["password"]),
        )
        for d in users_data
    ]
    db_session.bulk_save_objects(users)
    db_session.commit()

    count = db_session.query(User).count()
    assert count >= 10

# ======================================================================================
# Uniqueness Constraint Tests
# ======================================================================================

def test_unique_email_constraint(db_session):
    """Create two users with the same email and expect an IntegrityError."""
    first_user_data = create_fake_user()
    first_user = User(
        email=first_user_data["email"],
        username=first_user_data["username"],
        password_hash=User.hash_password(first_user_data["password"]),
    )
    db_session.add(first_user)
    db_session.commit()

    second_user_data = create_fake_user()
    second_user_data["email"] = first_user_data["email"]  # Force duplicate
    second_user = User(
        email=second_user_data["email"],
        username=second_user_data["username"],
        password_hash=User.hash_password(second_user_data["password"]),
    )
    db_session.add(second_user)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_username_constraint(db_session):
    """Create two users with the same username and expect an IntegrityError."""
    first_user_data = create_fake_user()
    first_user = User(
        email=first_user_data["email"],
        username=first_user_data["username"],
        password_hash=User.hash_password(first_user_data["password"]),
    )
    db_session.add(first_user)
    db_session.commit()

    second_user_data = create_fake_user()
    second_user_data["username"] = first_user_data["username"]  # Force duplicate
    second_user = User(
        email=second_user_data["email"],
        username=second_user_data["username"],
        password_hash=User.hash_password(second_user_data["password"]),
    )
    db_session.add(second_user)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

# ======================================================================================
# Persistence after Constraint Violation
# ======================================================================================

def test_user_persistence_after_constraint(db_session):
    """
    - Create and commit a valid user
    - Attempt to create a duplicate user (same email) -> fails
    - Confirm the original user still exists
    """
    initial_user = User(
        first_name="First",
        last_name="User",
        email="first@example.com",
        username="firstuser",
        password_hash="hashed_password123",
    )
    db_session.add(initial_user)
    db_session.commit()
    saved_id = initial_user.id

    try:
        duplicate_user = User(
            email="first@example.com",  # Duplicate
            username="seconduser",
            password_hash="hashed_password456",
        )
        db_session.add(duplicate_user)
        db_session.commit()
        assert False, "Should have raised IntegrityError"
    except IntegrityError:
        db_session.rollback()

    found_user = db_session.query(User).filter_by(id=saved_id).first()
    assert found_user is not None
    assert found_user.id == saved_id
    assert found_user.email == "first@example.com"
    assert found_user.username == "firstuser"

# ======================================================================================
# Error Handling Test
# ======================================================================================

def test_error_handling():
    """Verify that a manual managed_db_session can capture and log invalid SQL errors."""
    with pytest.raises(Exception) as exc_info:
        with managed_db_session() as session:
            session.execute(text("INVALID SQL"))
    assert "INVALID SQL" in str(exc_info.value)
