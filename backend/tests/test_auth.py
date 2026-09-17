"""
Comprehensive authentication test suite.

All tests use mocked UserRepository — no live MongoDB required.
Covers: hashing, verification, admin/officer auth, invalid password,
inactive account, logout, unauthenticated state, missing user, DB failure.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pymongo.errors import ServerSelectionTimeoutError

import streamlit as st
from models.user import User
from utils.security import hash_password, verify_password
from services.auth_service import AuthService
from auth.authentication import (
    authenticate_user,
    login_user,
    logout_user,
    get_current_user,
    is_authenticated,
    AUTH_SESSION_KEYS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_user(name, email, password, role, user_id=1, is_active=True):
    """Helper to create a User with a properly hashed password."""
    return User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        id=user_id,
        is_active=is_active,
    )


@pytest.fixture
def admin_user():
    return _make_user("Admin", "admin@missingtracker.com", "admin123", "admin", user_id=1)


@pytest.fixture
def officer_user():
    return _make_user("Officer", "officer@missingtracker.com", "officer123", "officer", user_id=2)


@pytest.fixture
def inactive_user():
    return _make_user("Inactive", "inactive@test.com", "secret", "officer", user_id=3, is_active=False)


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def mock_session(monkeypatch):
    """Mocks st.session_state as a plain dict-like object for testing."""
    session_dict = {}

    class MockSessionState:
        def __getitem__(self, key):
            return session_dict[key]

        def __setitem__(self, key, value):
            session_dict[key] = value

        def __contains__(self, key):
            return key in session_dict

        def __delitem__(self, key):
            del session_dict[key]

        def get(self, key, default=None):
            return session_dict.get(key, default)

        def __getattr__(self, key):
            try:
                return session_dict[key]
            except KeyError:
                raise AttributeError(key)

        def __setattr__(self, key, value):
            session_dict[key] = value

    monkeypatch.setattr(st, "session_state", MockSessionState())
    # Prevent logout from calling st.rerun()
    monkeypatch.setattr(st, "rerun", lambda: None, raising=False)
    monkeypatch.setattr(st, "experimental_rerun", lambda: None, raising=False)
    return session_dict


# ---------------------------------------------------------------------------
# 1. Password Hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        raw = "SuperSecret123"
        hashed = hash_password(raw)
        assert hashed != raw

    def test_hash_is_bcrypt_format(self):
        hashed = hash_password("test")
        assert hashed.startswith("$2b$")

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt each time


# ---------------------------------------------------------------------------
# 2. Password Verification
# ---------------------------------------------------------------------------

class TestPasswordVerification:
    def test_correct_password(self):
        hashed = hash_password("correct_horse_battery_staple")
        assert verify_password("correct_horse_battery_staple", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_hash(self):
        assert verify_password("anything", "") is False
        assert verify_password("anything", None) is False


# ---------------------------------------------------------------------------
# 3. Successful Admin Authentication
# ---------------------------------------------------------------------------

class TestAdminAuthentication:
    def test_admin_login_success(self, admin_user, mock_repo):
        mock_repo.get_by_email.return_value = admin_user
        service = AuthService(user_repo=mock_repo)

        result = service.authenticate("admin@missingtracker.com", "admin123")

        assert result is not None
        assert result.role == "admin"
        assert result.email == "admin@missingtracker.com"
        mock_repo.get_by_email.assert_called_once_with("admin@missingtracker.com")


# ---------------------------------------------------------------------------
# 4. Successful Officer Authentication
# ---------------------------------------------------------------------------

class TestOfficerAuthentication:
    def test_officer_login_success(self, officer_user, mock_repo):
        mock_repo.get_by_email.return_value = officer_user
        service = AuthService(user_repo=mock_repo)

        result = service.authenticate("officer@missingtracker.com", "officer123")

        assert result is not None
        assert result.role == "officer"
        assert result.email == "officer@missingtracker.com"


# ---------------------------------------------------------------------------
# 5. Invalid Password
# ---------------------------------------------------------------------------

class TestInvalidPassword:
    def test_wrong_password_returns_none(self, admin_user, mock_repo):
        mock_repo.get_by_email.return_value = admin_user
        service = AuthService(user_repo=mock_repo)

        result = service.authenticate("admin@missingtracker.com", "wrong_password")

        assert result is None


# ---------------------------------------------------------------------------
# 6. Inactive Account
# ---------------------------------------------------------------------------

class TestInactiveAccount:
    def test_inactive_raises_value_error(self, inactive_user, mock_repo):
        mock_repo.get_by_email.return_value = inactive_user
        service = AuthService(user_repo=mock_repo)

        with pytest.raises(ValueError, match="inactive"):
            service.authenticate("inactive@test.com", "secret")


# ---------------------------------------------------------------------------
# 7. Logout Clears Session
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_clears_all_auth_keys(self, mock_session):
        # Set up authenticated session
        st.session_state["authenticated"] = True
        st.session_state["user"] = {"id": 1, "username": "admin", "role": "admin", "email": "a@b.com"}

        logout_user()

        for key in AUTH_SESSION_KEYS:
            assert key not in mock_session


# ---------------------------------------------------------------------------
# 8. Unauthenticated State
# ---------------------------------------------------------------------------

class TestUnauthenticatedState:
    def test_get_current_user_returns_none(self, mock_session):
        assert get_current_user() is None

    def test_is_authenticated_returns_false(self, mock_session):
        assert is_authenticated() is False


# ---------------------------------------------------------------------------
# Additional Edge Cases
# ---------------------------------------------------------------------------

class TestMissingUser:
    def test_email_not_found_returns_none(self, mock_repo):
        mock_repo.get_by_email.return_value = None
        service = AuthService(user_repo=mock_repo)

        result = service.authenticate("nonexistent@example.com", "any_password")

        assert result is None


class TestMongoDBConnectionFailure:
    def test_connection_failure_raises_connection_error(self, mock_repo):
        mock_repo.get_by_email.side_effect = ServerSelectionTimeoutError("timeout")
        service = AuthService(user_repo=mock_repo)

        with pytest.raises(ConnectionError, match="Unable to connect"):
            service.authenticate("admin@missingtracker.com", "admin123")


class TestSessionLoginFlow:
    def test_login_stores_minimal_user_data(self, mock_session):
        user_data = {
            "id": 1,
            "username": "admin",
            "name": "Admin",
            "role": "admin",
            "email": "admin@missing.com",
            "password_hash": "should_not_be_stored",
            "is_active": True,
            "created_at": "2026-01-01",
        }
        login_user(user_data)

        stored = st.session_state["user"]
        assert stored["id"] == 1
        assert stored["username"] == "admin"
        assert stored["role"] == "admin"
        assert stored["email"] == "admin@missing.com"
        # Sensitive data must NOT be stored in session
        assert "password_hash" not in stored
        assert "is_active" not in stored
        assert "created_at" not in stored

    def test_is_authenticated_after_login(self, mock_session):
        login_user({"id": 1, "username": "a", "role": "admin", "email": "a@b.com"})
        assert is_authenticated() is True
        assert get_current_user() is not None
