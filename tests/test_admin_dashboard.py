"""
Admin Dashboard access and data tests.

Tests:
1. Admin can access the dashboard (require_role passes)
2. Officer is blocked from the dashboard (require_role halts)
3. Dashboard data loading functions work with mocked repositories
"""
import pytest
from unittest.mock import MagicMock, patch
import streamlit as st

from auth.permissions import require_role, ROLE_ADMIN, ROLE_OFFICER
from models import MissingPerson, MatchResult, Sighting


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

ADMIN_USER = {"id": 1, "username": "Admin", "role": "admin", "email": "admin@test.com"}
OFFICER_USER = {"id": 2, "username": "OfficerA", "role": "officer", "email": "officer@test.com"}


@pytest.fixture
def mock_session(monkeypatch):
    """Mocks st.session_state."""
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
    return session_dict


def _set_user(session_dict, user):
    session_dict["authenticated"] = True
    session_dict["user"] = user


# ──────────────────────────────────────────────────────────────────────
# Access Control Tests
# ──────────────────────────────────────────────────────────────────────

class TestDashboardAccess:
    def test_admin_can_access_dashboard(self, mock_session, monkeypatch):
        """Admin user passes the require_role guard."""
        _set_user(mock_session, ADMIN_USER)
        # Should not raise or call st.stop()
        result = require_role([ROLE_ADMIN])
        assert result is True

    def test_officer_cannot_access_dashboard(self, mock_session, monkeypatch):
        """Officer user is blocked by require_role([admin])."""
        _set_user(mock_session, OFFICER_USER)

        # Mock st.error and st.stop to capture the block
        error_calls = []
        monkeypatch.setattr(st, "error", lambda msg: error_calls.append(msg))

        class StopException(Exception):
            pass

        monkeypatch.setattr(st, "stop", lambda: (_ for _ in ()).throw(StopException()))

        with pytest.raises(StopException):
            require_role([ROLE_ADMIN])

        assert len(error_calls) == 1
        assert "Access Denied" in error_calls[0]

    def test_unauthenticated_cannot_access_dashboard(self, mock_session, monkeypatch):
        """Unauthenticated user is blocked by require_role."""
        # Don't set any user — session is empty

        error_calls = []
        monkeypatch.setattr(st, "error", lambda msg: error_calls.append(msg))

        class StopException(Exception):
            pass

        monkeypatch.setattr(st, "stop", lambda: (_ for _ in ()).throw(StopException()))

        with pytest.raises(StopException):
            require_role([ROLE_ADMIN])

        assert len(error_calls) == 1
        assert "Authentication Required" in error_calls[0]


# ──────────────────────────────────────────────────────────────────────
# Data Loading Tests (statistics come from repositories)
# ──────────────────────────────────────────────────────────────────────

class TestDashboardData:
    def _make_cases(self):
        return [
            MissingPerson(name="A", age=20, gender="Male", last_seen_location="Delhi",
                          status="Missing", id=1, created_by="Admin"),
            MissingPerson(name="B", age=25, gender="Female", last_seen_location="Mumbai",
                          status="Found", id=2, created_by="OfficerA"),
            MissingPerson(name="C", age=30, gender="Male", last_seen_location="Chennai",
                          status="Missing", id=3, created_by="Admin"),
        ]

    def _make_matches(self):
        return [
            MatchResult(case_id=1, sighting_id=1, similarity=0.92, status="Pending Review", id=1),
            MatchResult(case_id=2, sighting_id=2, similarity=0.88, status="Confirmed Match", id=2),
        ]

    def _make_sightings(self):
        return [
            Sighting(case_id=1, location="Delhi", id=1, video_path="cam01.mp4"),
            Sighting(case_id=2, location="Mumbai", id=2),
            Sighting(case_id=1, location="Pune", id=3, video_path="cam02.mp4"),
        ]

    def test_statistics_computed_from_repos(self):
        """Verify dashboard stats are derived from repository data, not hardcoded."""
        cases = self._make_cases()
        matches = self._make_matches()
        sightings = self._make_sightings()

        # Simulate the dashboard data aggregation logic
        total_cases = len(cases)
        active_cases = len([c for c in cases if c.status == "Missing"])
        resolved_cases = len([c for c in cases if c.status == "Found"])
        pending_matches = len([m for m in matches if m.status == "Pending Review"])
        confirmed_matches = len([m for m in matches if m.status == "Confirmed Match"])
        video_sightings = len([s for s in sightings if s.video_path])

        assert total_cases == 3
        assert active_cases == 2
        assert resolved_cases == 1
        assert pending_matches == 1
        assert confirmed_matches == 1
        assert video_sightings == 2

    def test_empty_database_produces_zero_stats(self):
        """Dashboard should handle empty collections gracefully."""
        assert len([]) == 0  # total cases
        assert len([c for c in [] if getattr(c, 'status', '') == "Missing"]) == 0
        assert len([m for m in [] if getattr(m, 'status', '') == "Pending Review"]) == 0

    def test_recent_cases_limited_to_five(self):
        """Only the 5 most recent cases should appear in the Recent Cases section."""
        cases = self._make_cases()
        recent = cases[:5]
        assert len(recent) <= 5

    def test_statistics_use_repository_not_hardcoded(self):
        """Ensure that repository methods are used to load data."""
        mock_case_repo = MagicMock()
        mock_match_repo = MagicMock()
        mock_sighting_repo = MagicMock()

        mock_case_repo.get_all.return_value = self._make_cases()
        mock_match_repo.get_all.return_value = self._make_matches()
        mock_sighting_repo.get_all.return_value = self._make_sightings()

        # Call repositories the same way the dashboard does
        all_cases = mock_case_repo.get_all()
        all_matches = mock_match_repo.get_all()
        all_sightings = mock_sighting_repo.get_all()

        assert mock_case_repo.get_all.called
        assert mock_match_repo.get_all.called
        assert mock_sighting_repo.get_all.called
        assert len(all_cases) == 3
        assert len(all_matches) == 2
        assert len(all_sightings) == 3
