"""
Comprehensive role-based authorization test suite.

Tests every Admin/Officer permission boundary:
- Session-aware permission functions (via mocked st.session_state)
- Service-layer authorize_* helpers (no Streamlit dependency)
- CaseService authorization enforcement (with mocked CaseRepository)
- MatchReviewService authorization enforcement (with mocked repos)

All tests use mocked repositories — no live MongoDB required.
"""
import pytest
from unittest.mock import MagicMock, patch
import streamlit as st

from auth.permissions import (
    ROLE_ADMIN, ROLE_OFFICER,
    is_admin, is_officer,
    can_create_case, can_view_all_cases, can_edit_case,
    can_delete_case, can_trigger_matching, can_process_video,
    can_review_match, can_view_map, can_manage_users, can_view_reports,
    # Service-layer helpers
    authorize_view_cases, authorize_edit_case, authorize_delete_case,
    authorize_trigger_matching, authorize_process_video,
    authorize_review_match, authorize_manage_users,
)
from services.case_service import CaseService
from services.match_review import MatchReviewService
from models import MissingPerson, MatchResult


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

ADMIN_USER = {"id": 1, "username": "Admin", "role": "admin", "email": "admin@test.com"}
OFFICER_USER = {"id": 2, "username": "OfficerA", "role": "officer", "email": "officerA@test.com"}
OFFICER_B = {"id": 3, "username": "OfficerB", "role": "officer", "email": "officerB@test.com"}
PUBLIC_USER = {"id": 4, "username": "Public", "role": "public", "email": "pub@test.com"}


@pytest.fixture
def mock_session(monkeypatch):
    """Mocks st.session_state as a plain dict-like object."""
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
    """Inject a user into the mocked session state."""
    session_dict["authenticated"] = True
    session_dict["user"] = user


def _make_case(case_id, created_by):
    """Create a MissingPerson stub with id and created_by."""
    return MissingPerson(
        name="Test Person", age=25, gender="Male",
        last_seen_location="Delhi", created_by=created_by, id=case_id,
    )


def _make_match(match_id, case_id):
    """Create a MatchResult stub."""
    return MatchResult(
        case_id=case_id, sighting_id=1, confidence=0.9,
        status="Pending Review", id=match_id,
    )


# ══════════════════════════════════════════════════════════════════════
# PART 1: Role Checkers (session-aware)
# ══════════════════════════════════════════════════════════════════════

class TestRoleCheckers:
    def test_admin_is_admin(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert is_admin() is True
        assert is_officer() is False

    def test_officer_is_officer(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert is_officer() is True
        assert is_admin() is False

    def test_no_user_is_neither(self, mock_session):
        assert is_admin() is False
        assert is_officer() is False


# ══════════════════════════════════════════════════════════════════════
# PART 2: Session-aware Permission Functions
# ══════════════════════════════════════════════════════════════════════

class TestAdminPermissions:
    """Admin should have ALL permissions."""

    def test_can_create_case(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_create_case() is True

    def test_can_view_all_cases(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_view_all_cases() is True

    def test_can_edit_any_case(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_edit_case(case_created_by="AnyOfficer") is True

    def test_can_delete_case(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_delete_case() is True

    def test_can_trigger_matching(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_trigger_matching() is True

    def test_can_process_video(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_process_video() is True

    def test_can_review_match(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_review_match() is True

    def test_can_view_map(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_view_map() is True

    def test_can_manage_users(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_manage_users() is True

    def test_can_view_reports(self, mock_session):
        _set_user(mock_session, ADMIN_USER)
        assert can_view_reports() is True


class TestOfficerPermissions:
    """Officer should have limited permissions."""

    def test_can_create_case(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_create_case() is True

    def test_cannot_view_all_cases(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_view_all_cases() is False

    def test_can_edit_own_case(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_edit_case(case_created_by="OfficerA") is True

    def test_cannot_edit_other_case(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_edit_case(case_created_by="OfficerB") is False

    def test_cannot_delete_case(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_delete_case() is False

    def test_cannot_trigger_matching(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_trigger_matching() is False

    def test_cannot_process_video(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_process_video() is False

    def test_cannot_review_match(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_review_match() is False

    def test_cannot_view_map(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_view_map() is False

    def test_cannot_manage_users(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_manage_users() is False

    def test_cannot_view_reports(self, mock_session):
        _set_user(mock_session, OFFICER_USER)
        assert can_view_reports() is False


# ══════════════════════════════════════════════════════════════════════
# PART 3: Service-layer authorize_* helpers (no Streamlit needed)
# ══════════════════════════════════════════════════════════════════════

class TestAuthorizeViewCases:
    def test_admin_gets_no_filter(self):
        result = authorize_view_cases(ADMIN_USER)
        assert result is None  # no restriction

    def test_officer_gets_ownership_filter(self):
        result = authorize_view_cases(OFFICER_USER)
        assert result == {"created_by": "OfficerA"}

    def test_public_raises_permission_error(self):
        with pytest.raises(PermissionError):
            authorize_view_cases(PUBLIC_USER)


class TestAuthorizeEditCase:
    def test_admin_can_edit_any(self):
        assert authorize_edit_case(ADMIN_USER, "AnyOfficer") is True

    def test_officer_can_edit_own(self):
        assert authorize_edit_case(OFFICER_USER, "OfficerA") is True

    def test_officer_cannot_edit_others(self):
        with pytest.raises(PermissionError, match="own cases"):
            authorize_edit_case(OFFICER_USER, "OfficerB")

    def test_public_cannot_edit(self):
        with pytest.raises(PermissionError):
            authorize_edit_case(PUBLIC_USER, "anyone")


class TestAuthorizeDeleteCase:
    def test_admin_can_delete(self):
        assert authorize_delete_case(ADMIN_USER) is True

    def test_officer_cannot_delete(self):
        with pytest.raises(PermissionError, match="administrators"):
            authorize_delete_case(OFFICER_USER)


class TestAuthorizeTriggerMatching:
    def test_admin_can_trigger(self):
        assert authorize_trigger_matching(ADMIN_USER) is True

    def test_officer_cannot_trigger(self):
        with pytest.raises(PermissionError, match="face matching"):
            authorize_trigger_matching(OFFICER_USER)


class TestAuthorizeProcessVideo:
    def test_admin_can_process(self):
        assert authorize_process_video(ADMIN_USER) is True

    def test_officer_cannot_process(self):
        with pytest.raises(PermissionError, match="video"):
            authorize_process_video(OFFICER_USER)


class TestAuthorizeReviewMatch:
    def test_admin_can_review(self):
        assert authorize_review_match(ADMIN_USER) is True

    def test_officer_cannot_review(self):
        with pytest.raises(PermissionError, match="review matches"):
            authorize_review_match(OFFICER_USER)


class TestAuthorizeManageUsers:
    def test_admin_can_manage(self):
        assert authorize_manage_users(ADMIN_USER) is True

    def test_officer_cannot_manage(self):
        with pytest.raises(PermissionError, match="manage users"):
            authorize_manage_users(OFFICER_USER)


# ══════════════════════════════════════════════════════════════════════
# PART 4: CaseService authorization enforcement
# ══════════════════════════════════════════════════════════════════════

class TestCaseServiceAdminAuth:
    """Admin should be able to do everything through CaseService."""

    def test_admin_register_case(self):
        mock_repo = MagicMock()
        mock_repo.create.return_value = _make_case(1, "Admin")
        svc = CaseService(case_repo=mock_repo)

        result = svc.register_case(
            name="Test", age=20, gender="Male",
            last_seen_location="Delhi", current_user=ADMIN_USER,
        )
        assert result is not None
        mock_repo.create.assert_called_once()

    def test_admin_view_all_cases(self):
        mock_repo = MagicMock()
        mock_repo.get_all.return_value = [_make_case(1, "OfficerA"), _make_case(2, "OfficerB")]
        svc = CaseService(case_repo=mock_repo)

        cases = svc.get_all_cases(current_user=ADMIN_USER)
        assert len(cases) == 2
        # Admin should get no created_by filter
        mock_repo.get_all.assert_called_once_with(None)

    def test_admin_view_any_single_case(self):
        case = _make_case(1, "OfficerA")
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case
        svc = CaseService(case_repo=mock_repo)

        result = svc.get_case(1, current_user=ADMIN_USER)
        assert result == case

    def test_admin_edit_any_case(self):
        case = _make_case(1, "OfficerA")
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case
        mock_repo.update_status.return_value = True
        svc = CaseService(case_repo=mock_repo)

        result = svc.update_case_status(1, "Found", current_user=ADMIN_USER)
        assert result is True

    def test_admin_delete_case(self):
        mock_repo = MagicMock()
        mock_repo.delete.return_value = True
        svc = CaseService(case_repo=mock_repo)

        result = svc.delete_case(1, current_user=ADMIN_USER)
        assert result is True


class TestCaseServiceOfficerAuth:
    """Officer should be restricted to own cases and cannot delete."""

    def test_officer_register_case(self):
        mock_repo = MagicMock()
        mock_repo.create.return_value = _make_case(1, "OfficerA")
        svc = CaseService(case_repo=mock_repo)

        result = svc.register_case(
            name="Test", age=20, gender="Male",
            last_seen_location="Delhi", current_user=OFFICER_USER,
        )
        assert result is not None

    def test_officer_view_own_cases_only(self):
        mock_repo = MagicMock()
        mock_repo.get_all.return_value = [_make_case(1, "OfficerA")]
        svc = CaseService(case_repo=mock_repo)

        svc.get_all_cases(current_user=OFFICER_USER)
        # Should have been called with the ownership filter
        call_args = mock_repo.get_all.call_args[0][0]
        assert call_args["created_by"] == "OfficerA"

    def test_officer_can_view_own_single_case(self):
        case = _make_case(1, "OfficerA")
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case
        svc = CaseService(case_repo=mock_repo)

        result = svc.get_case(1, current_user=OFFICER_USER)
        assert result == case

    def test_officer_cannot_view_other_officers_case(self):
        case = _make_case(1, "OfficerB")
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError, match="own cases"):
            svc.get_case(1, current_user=OFFICER_USER)

    def test_officer_can_edit_own_case(self):
        case = _make_case(1, "OfficerA")
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case
        mock_repo.update_status.return_value = True
        svc = CaseService(case_repo=mock_repo)

        result = svc.update_case_status(1, "Found", current_user=OFFICER_USER)
        assert result is True

    def test_officer_cannot_edit_other_officers_case(self):
        case = _make_case(1, "OfficerB")
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError, match="own cases"):
            svc.update_case_status(1, "Found", current_user=OFFICER_USER)

    def test_officer_cannot_delete_case(self):
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError, match="administrators"):
            svc.delete_case(1, current_user=OFFICER_USER)


class TestCaseServicePublicDenied:
    """Public role should be denied from all case operations."""

    def test_public_cannot_register(self):
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError):
            svc.register_case(
                name="Test", age=20, gender="Male",
                last_seen_location="Delhi", current_user=PUBLIC_USER,
            )

    def test_public_cannot_view_cases(self):
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError):
            svc.get_all_cases(current_user=PUBLIC_USER)

    def test_public_cannot_delete(self):
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError):
            svc.delete_case(1, current_user=PUBLIC_USER)


# ══════════════════════════════════════════════════════════════════════
# PART 5: MatchReviewService authorization enforcement
# ══════════════════════════════════════════════════════════════════════

class TestMatchReviewAdminAuth:
    def test_admin_can_get_pending_reviews(self):
        mock_match_repo = MagicMock()
        mock_match_repo.get_all.return_value = [_make_match(1, 1)]
        svc = MatchReviewService(match_repo=mock_match_repo)

        reviews = svc.get_pending_reviews(current_user=ADMIN_USER)
        assert len(reviews) == 1

    def test_admin_can_confirm_match(self):
        mock_match_repo = MagicMock()
        mock_case_repo = MagicMock()
        mock_match_repo.get_by_id.return_value = _make_match(1, 1)
        mock_match_repo.update_status.return_value = True
        svc = MatchReviewService(match_repo=mock_match_repo, case_repo=mock_case_repo)

        result = svc.review_match(1, "Confirmed Match", current_user=ADMIN_USER)
        assert result is True

    def test_admin_can_reject_match(self):
        mock_match_repo = MagicMock()
        mock_case_repo = MagicMock()
        mock_match_repo.get_by_id.return_value = _make_match(1, 1)
        mock_match_repo.update_status.return_value = True
        svc = MatchReviewService(match_repo=mock_match_repo, case_repo=mock_case_repo)

        result = svc.review_match(1, "False Positive", current_user=ADMIN_USER)
        assert result is True


class TestMatchReviewOfficerDenied:
    def test_officer_cannot_get_pending_reviews(self):
        mock_match_repo = MagicMock()
        svc = MatchReviewService(match_repo=mock_match_repo)

        with pytest.raises(PermissionError, match="review matches"):
            svc.get_pending_reviews(current_user=OFFICER_USER)

    def test_officer_cannot_confirm_match(self):
        mock_match_repo = MagicMock()
        svc = MatchReviewService(match_repo=mock_match_repo)

        with pytest.raises(PermissionError, match="review matches"):
            svc.review_match(1, "Confirmed Match", current_user=OFFICER_USER)

    def test_officer_cannot_reject_match(self):
        mock_match_repo = MagicMock()
        svc = MatchReviewService(match_repo=mock_match_repo)

        with pytest.raises(PermissionError, match="review matches"):
            svc.review_match(1, "False Positive", current_user=OFFICER_USER)
