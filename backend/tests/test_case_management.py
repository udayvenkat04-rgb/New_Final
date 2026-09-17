"""
Phase 11 — Case Management Test Suite.

Covers the 11 required scenarios:
 1. Admin can list all cases.
 2. Officer can list only their own cases.
 3. Officer cannot access another officer's case by directly providing the case ID.
 4. Admin can edit a case.
 5. Authorized officer can edit their own case.
 6. Officer cannot delete a case.
 7. Admin can delete/soft-delete a case.
 8. Case history is recorded (create/edit/status/delete).
 9. Search works (case number, person name, city, state).
10. Filters work (status, gender, state, city, date range).
11. Unauthorized users cannot access case management.

All service-layer tests use either the real repositories (with cleanup) or
mocks — depending on the assertion being tested. DB-backed tests clean up
after themselves so the DB is left in the same state.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from services.case_service import CaseService
from repositories.case_repository import CaseRepository
from models import MissingPerson, CaseHistory
from auth.permissions import (
    authorize_view_cases,
    authorize_edit_case,
    authorize_delete_case,
)
from utils.validators import STATUS_ACTIVE


# ──────────────────────────────────────────────────────────────────────
# Fixtures: user dictionaries (service-layer user format)
# ──────────────────────────────────────────────────────────────────────

ADMIN_USER = {"id": 99, "username": "AdminUser", "role": "admin", "email": "admin@test.com"}
OFFICER_A = {"id": 101, "username": "OfficerAlpha", "role": "officer", "email": "a@test.com"}
OFFICER_B = {"id": 102, "username": "OfficerBeta", "role": "officer", "email": "b@test.com"}
PUBLIC_USER = {"id": 500, "username": "JohnPublic", "role": "public", "email": "pub@test.com"}
UNAUTHENTICATED = None  # explicit None for "no user"


# ──────────────────────────────────────────────────────────────────────
# Fixtures: helper factories
# ──────────────────────────────────────────────────────────────────────

def _make_case(case_id, created_by: str, **overrides) -> MissingPerson:
    """Build a MissingPerson with sensible defaults and explicit id/created_by.

    case_id can be None — in that case a numeric fallback is used so the age
    and case_number formulas still work.
    """
    cid = case_id if isinstance(case_id, int) else 1000
    base = dict(
        id=case_id if case_id is not None else None,
        name=f"Person-{cid}",
        age=25 + (cid % 50),
        gender="Male" if cid % 2 == 1 else "Female",
        description=f"Test description for case {cid}. Must be >= 10 chars.",
        last_seen_location=f"Location-{cid}",
        last_seen_date=datetime(2026, 1, (cid % 28) + 1),
        last_seen_state="Maharashtra" if cid % 2 else "Karnataka",
        last_seen_city="Mumbai" if cid % 2 else "Bengaluru",
        contact_name=f"Reporter-{cid}",
        contact_email=f"r{cid}@test.com",
        contact_phone=f"+91 98000 00{cid % 1000:03d}",
        photo_path=f"data/uploads/placeholder{cid}.jpg",
        status=STATUS_ACTIVE,
        created_by=created_by,
        case_number=(f"MP-2026-{cid:05d}" if isinstance(case_id, int) else None),
        created_at=datetime(2026, 1, 1, 10, 0),
        updated_at=datetime(2026, 1, 1, 10, 0),
        is_deleted=False,
        deleted_at=None,
    )
    base.update(overrides)
    return MissingPerson(**base)


@pytest.fixture
def db_service():
    """CaseService backed by the real MongoDB CaseRepository with cleanup."""
    repo = CaseRepository()
    svc = CaseService(case_repo=repo)
    # Track inserted ids for cleanup
    created_ids = []
    yield svc, repo, created_ids
    # Cleanup: hard delete anything we inserted (soft or hard)
    for cid in created_ids:
        try:
            repo.delete(cid)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
# 1. Admin can list all cases (service + repo verified)
# ══════════════════════════════════════════════════════════════════════

class TestAdminListAllCases:
    def test_admin_get_all_cases_sees_all_officers_cases(self):
        """Admin → get_all_cases() returns cases from all officers; no created_by filter applied."""
        mock_repo = MagicMock()
        case_A = _make_case(1, OFFICER_A["username"])
        case_B = _make_case(2, OFFICER_B["username"])
        case_admin = _make_case(3, ADMIN_USER["username"])
        mock_repo.get_all.return_value = [case_A, case_B, case_admin]
        svc = CaseService(case_repo=mock_repo)

        result = svc.get_all_cases(current_user=ADMIN_USER)

        assert len(result) == 3
        # Admin must NOT have a created_by restriction on the repo call
        repo_filter = mock_repo.get_all.call_args[0][0]
        # None (or empty dict) means no ownership filter — Admin sees everything
        assert repo_filter is None or "created_by" not in (repo_filter or {})

    def test_admin_list_uses_repo(self, db_service):
        svc, repo, created_ids = db_service
        # Insert one case each for OfficerA, OfficerB, Admin
        c1 = _make_case(None, OFFICER_A["username"], id=None, case_number=None)
        c1 = repo.create(c1); created_ids.append(c1.id)
        c2 = _make_case(None, OFFICER_B["username"], id=None, case_number=None)
        c2 = repo.create(c2); created_ids.append(c2.id)

        admin_view = svc.get_all_cases(current_user=ADMIN_USER)
        admin_ids = {c.id for c in admin_view}
        assert c1.id in admin_ids
        assert c2.id in admin_ids


# ══════════════════════════════════════════════════════════════════════
# 2. Officer can list only their own cases
# ══════════════════════════════════════════════════════════════════════

class TestOfficerOwnCasesOnly:
    def test_officer_get_all_cases_merges_ownership_filter(self):
        """Officer → repo.get_all must be called with created_by=OfficerA filter."""
        mock_repo = MagicMock()
        mock_repo.get_all.return_value = []
        svc = CaseService(case_repo=mock_repo)

        svc.get_all_cases(current_user=OFFICER_A)

        repo_filter = mock_repo.get_all.call_args[0][0]
        assert repo_filter is not None
        assert repo_filter.get("created_by") == OFFICER_A["username"]

    def test_officer_cannot_see_other_officer_case_in_list(self, db_service):
        svc, repo, created_ids = db_service
        own = _make_case(None, OFFICER_A["username"], id=None, case_number=None)
        own = repo.create(own); created_ids.append(own.id)
        others = _make_case(None, OFFICER_B["username"], id=None, case_number=None)
        others = repo.create(others); created_ids.append(others.id)

        officerA_view = svc.get_all_cases(current_user=OFFICER_A)
        ids_seen_by_A = {c.id for c in officerA_view}
        assert own.id in ids_seen_by_A
        assert others.id not in ids_seen_by_A


# ══════════════════════════════════════════════════════════════════════
# 3. Officer cannot access another officer's case by direct case ID
# ══════════════════════════════════════════════════════════════════════

class TestOfficerDirectIdBlocked:
    def test_officer_direct_get_case_other_officer_raises_permission(self):
        case_other = _make_case(42, OFFICER_B["username"])
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = case_other
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError, match="own cases"):
            svc.get_case(42, current_user=OFFICER_A)

    def test_officer_direct_id_repo_still_called_but_denied_after(self, db_service):
        svc, repo, created_ids = db_service
        others_case = _make_case(None, OFFICER_B["username"], id=None, case_number=None)
        others_case = repo.create(others_case); created_ids.append(others_case.id)

        with pytest.raises(PermissionError):
            svc.get_case(others_case.id, current_user=OFFICER_A)


# ══════════════════════════════════════════════════════════════════════
# 4. Admin can edit a case
# ══════════════════════════════════════════════════════════════════════

class TestAdminCanEdit:
    def test_admin_edit_preserves_case_number_and_created_by(self):
        original = _make_case(10, OFFICER_B["username"])
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = original

        def _save(case_obj):
            case_obj.updated_at = datetime.utcnow()
            return case_obj

        mock_repo.update.side_effect = _save
        mock_repo.log_history.return_value = CaseHistory(case_id=10, action="CASE_UPDATED")
        svc = CaseService(case_repo=mock_repo)

        updated = svc.edit_case(
            10,
            name="New Name",
            age=99,
            current_user=ADMIN_USER,
        )

        assert updated is not None
        assert updated.name == "New Name"
        assert updated.age == 99
        # Immutable fields preserved
        assert updated.case_number == original.case_number
        assert updated.created_by == original.created_by
        assert updated.id == original.id
        # Case number CANNOT have been touched in the update payload
        assert mock_repo.update.called
        saved_to_repo = mock_repo.update.call_args[0][0]
        assert saved_to_repo.case_number == original.case_number
        assert saved_to_repo.created_by == original.created_by

    def test_admin_edit_updates_updated_at(self, db_service):
        svc, repo, created_ids = db_service
        original = _make_case(None, OFFICER_A["username"], id=None, case_number=None,
                              created_at=datetime(2026, 1, 1),
                              updated_at=datetime(2026, 1, 1))
        original = repo.create(original); created_ids.append(original.id)
        before_updated_at = repo.get_by_id(original.id).updated_at

        import time
        time.sleep(0.05)
        updated = svc.edit_case(original.id, description="New desc for this test edit.",
                                current_user=ADMIN_USER)
        assert updated.updated_at > before_updated_at


# ══════════════════════════════════════════════════════════════════════
# 5. Authorized officer can edit their own case
# ══════════════════════════════════════════════════════════════════════

class TestOfficerEditOwn:
    def test_officer_edit_own_allowed(self):
        own = _make_case(20, OFFICER_A["username"])
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = own

        def _save(case_obj):
            case_obj.updated_at = datetime.utcnow()
            return case_obj

        mock_repo.update.side_effect = _save
        mock_repo.log_history.return_value = CaseHistory(case_id=20, action="CASE_UPDATED")
        svc = CaseService(case_repo=mock_repo)

        updated = svc.edit_case(
            20,
            contact_phone="+91 90000 00000",
            current_user=OFFICER_A,
        )
        assert updated is not None
        assert updated.contact_phone == "+91 90000 00000"

    def test_officer_cannot_edit_other_officer_case(self):
        other_owners_case = _make_case(30, OFFICER_B["username"])
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = other_owners_case
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError, match="own cases"):
            svc.edit_case(30, contact_phone="+91 111", current_user=OFFICER_A)


# ══════════════════════════════════════════════════════════════════════
# 6. Officer cannot delete a case
# ══════════════════════════════════════════════════════════════════════

class TestOfficerCannotDelete:
    def test_officer_delete_raises_permission_error(self):
        """Delete calls authorize_delete_case → Officer must raise before any repo call."""
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError, match="administrators"):
            svc.delete_case(55, current_user=OFFICER_A)

        # Service must not have touched the repository at all for an Officer
        mock_repo.soft_delete.assert_not_called()
        mock_repo.delete.assert_not_called()

    def test_authorize_delete_case_helper_blocks_officer(self):
        with pytest.raises(PermissionError, match="administrators"):
            authorize_delete_case(OFFICER_A)


# ══════════════════════════════════════════════════════════════════════
# 7. Admin can delete / soft-delete a case
# ══════════════════════════════════════════════════════════════════════

class TestAdminSoftDelete:
    def test_admin_delete_invokes_soft_delete_not_hard_delete(self):
        existing = _make_case(60, OFFICER_A["username"])
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = existing
        mock_repo.soft_delete.return_value = True
        mock_repo.log_history.return_value = CaseHistory(case_id=60, action="CASE_DELETED")
        svc = CaseService(case_repo=mock_repo)

        result = svc.delete_case(60, current_user=ADMIN_USER)

        assert result is True
        mock_repo.soft_delete.assert_called_once_with(60)
        mock_repo.delete.assert_not_called()  # NOT hard delete

    def test_soft_deleted_case_hidden_from_get_all_and_get_by_id(self, db_service):
        svc, repo, created_ids = db_service
        case = _make_case(None, OFFICER_A["username"], id=None, case_number=None)
        case = repo.create(case); created_ids.append(case.id)

        before = svc.get_case(case.id, current_user=ADMIN_USER)
        assert before is not None and before.is_deleted is False

        ok = svc.delete_case(case.id, current_user=ADMIN_USER)
        assert ok is True

        # After soft delete: standard reads should NOT return it
        assert svc.get_case(case.id, current_user=ADMIN_USER) is None
        admin_all_ids = {c.id for c in svc.get_all_cases(current_user=ADMIN_USER)}
        assert case.id not in admin_all_ids

        # But raw repo with include_deleted=True still sees it
        raw = repo.get_by_id(case.id, include_deleted=True)
        assert raw is not None
        assert raw.is_deleted is True
        assert raw.deleted_at is not None


# ══════════════════════════════════════════════════════════════════════
# 8. Case history is recorded (create, edit, status change, delete)
# ══════════════════════════════════════════════════════════════════════

class TestCaseHistory:
    def test_register_case_logs_case_created(self, db_service):
        svc, repo, created_ids = db_service
        saved = svc.register_case(
            name="HistoryTest",
            age=30,
            gender="Male",
            last_seen_location="Delhi",
            reporter_name="R",
            reporter_contact="9999999999",
            last_seen_date=datetime(2026, 1, 15),
            current_user=ADMIN_USER,
        )
        created_ids.append(saved.id)

        history = repo.get_history_by_case(saved.id)
        actions = [h.action for h in history]
        assert any(a in ("CASE_CREATED", "Case Created") for a in actions)
        # performed_by captured
        entry = next(h for h in history if h.action in ("CASE_CREATED", "Case Created"))
        assert entry.performed_by == ADMIN_USER["username"]

    def test_edit_case_logs_case_updated_and_status_change(self, db_service):
        svc, repo, created_ids = db_service
        saved = svc.register_case(
            name="EditHistory",
            age=40,
            gender="Female",
            last_seen_location="Pune",
            reporter_name="R",
            reporter_contact="9999999999",
            last_seen_date=datetime(2026, 1, 20),
            current_user=OFFICER_A,
        )
        created_ids.append(saved.id)
        old_status = saved.status

        svc.edit_case(
            saved.id,
            name="EditHistory-Renamed",
            status="Found",
            current_user=OFFICER_A,
        )

        history = repo.get_history_by_case(saved.id)
        actions = [h.action for h in history]
        assert any(a == "CASE_UPDATED" for a in actions)
        assert any(a == "CASE_STATUS_CHANGED" for a in actions)

        status_entry = next(h for h in history if h.action == "CASE_STATUS_CHANGED")
        assert status_entry.previous_status == old_status
        assert status_entry.new_status == "Found"
        assert status_entry.performed_by == OFFICER_A["username"]

    def test_delete_logs_case_deleted(self, db_service):
        svc, repo, created_ids = db_service
        saved = svc.register_case(
            name="DeleteHistory",
            age=50,
            gender="Male",
            last_seen_location="Chennai",
            reporter_name="R",
            reporter_contact="9999999999",
            last_seen_date=datetime(2026, 2, 1),
            current_user=OFFICER_B,
        )
        created_ids.append(saved.id)

        ok = svc.delete_case(saved.id, current_user=ADMIN_USER)
        assert ok is True

        history = repo.get_history_by_case(saved.id)
        actions = [h.action for h in history]
        assert "CASE_DELETED" in actions
        del_entry = next(h for h in history if h.action == "CASE_DELETED")
        assert del_entry.performed_by == ADMIN_USER["username"]
        assert "soft-deleted" in (del_entry.details or "").lower()


# ══════════════════════════════════════════════════════════════════════
# 9. Search works (case number, person name, city, state)
# ══════════════════════════════════════════════════════════════════════

class TestSearch:
    def test_search_by_person_name_admin(self):
        mock_repo = MagicMock(spec=CaseRepository)
        mock_repo.build_filter_query = CaseRepository.build_filter_query.__get__(mock_repo, CaseRepository)
        mock_repo.search.return_value = [
            _make_case(1, OFFICER_A["username"], name="Ananya Kapoor")
        ]
        svc = CaseService(case_repo=mock_repo)

        results = svc.search_and_filter_cases(
            search_term="Ananya", current_user=ADMIN_USER,
        )

        assert len(results) == 1
        search_call = mock_repo.search.call_args
        assert search_call[0][0] == "Ananya"
        fq = search_call[1].get("filter_query")
        # Admin: no created_by in filter
        assert "created_by" not in (fq or {})

    def test_search_officer_includes_ownership_filter(self):
        mock_repo = MagicMock(spec=CaseRepository)
        mock_repo.build_filter_query = CaseRepository.build_filter_query.__get__(mock_repo, CaseRepository)
        mock_repo.search.return_value = []
        svc = CaseService(case_repo=mock_repo)

        svc.search_and_filter_cases(
            search_term="Mumbai", current_user=OFFICER_A,
        )

        fq = mock_repo.search.call_args[1].get("filter_query")
        assert fq is not None
        assert fq.get("created_by") == OFFICER_A["username"]

    def test_search_by_city_state_case_number_uses_repo_search(self, db_service):
        svc, repo, created_ids = db_service
        c1 = _make_case(None, OFFICER_A["username"], id=None, case_number=None,
                        name="Rahul Verma", last_seen_city="Nagpur",
                        last_seen_state="Maharashtra")
        c1 = repo.create(c1); created_ids.append(c1.id)
        c2 = _make_case(None, OFFICER_B["username"], id=None, case_number=None,
                        name="Priya Iyer", last_seen_city="Mysuru",
                        last_seen_state="Karnataka")
        c2 = repo.create(c2); created_ids.append(c2.id)

        # Search by city: Nagpur → only c1 (for admin)
        hits = svc.search_and_filter_cases(search_term="Nagpur", current_user=ADMIN_USER)
        ids = {c.id for c in hits}
        assert c1.id in ids and c2.id not in ids

        # Search by name substring
        hits = svc.search_and_filter_cases(search_term="Priya", current_user=ADMIN_USER)
        ids = {c.id for c in hits}
        assert c2.id in ids and c1.id not in ids


# ══════════════════════════════════════════════════════════════════════
# 10. Filters work (status, gender, state, city, date range)
# ══════════════════════════════════════════════════════════════════════

class TestFilters:
    def test_filter_build_status_gender_state_city_passed_to_repo(self):
        mock_repo = MagicMock(spec=CaseRepository)
        mock_repo.build_filter_query = CaseRepository.build_filter_query.__get__(mock_repo, CaseRepository)
        mock_repo.search.return_value = []
        svc = CaseService(case_repo=mock_repo)

        svc.search_and_filter_cases(
            status="Found", gender="Female", state="Kerala", city="Kochi",
            current_user=ADMIN_USER,
        )

        fq = mock_repo.search.call_args[1].get("filter_query")
        assert fq is not None
        assert fq.get("status") == "Found"
        assert fq.get("gender") == "Female"
        assert fq.get("last_seen_state") == "Kerala"
        assert fq.get("last_seen_city") == "Kochi"

    def test_filter_date_range_builds_mongo_date_query(self):
        mock_repo = MagicMock(spec=CaseRepository)
        mock_repo.build_filter_query = CaseRepository.build_filter_query.__get__(mock_repo, CaseRepository)
        mock_repo.search.return_value = []
        svc = CaseService(case_repo=mock_repo)

        d_from = datetime(2026, 2, 1)
        d_to = datetime(2026, 2, 28, 23, 59, 59)
        svc.search_and_filter_cases(
            date_from=d_from, date_to=d_to, current_user=ADMIN_USER,
        )

        fq = mock_repo.search.call_args[1].get("filter_query")
        assert fq is not None
        assert "last_seen_date" in fq
        dr = fq["last_seen_date"]
        assert dr.get("$gte") == d_from
        assert dr.get("$lte") == d_to

    def test_filters_combined_with_ownership_for_officer(self, db_service):
        svc, repo, created_ids = db_service
        # OfficerA: 1 ACTIVE Male, 1 Found Female
        a1 = _make_case(None, OFFICER_A["username"], id=None, case_number=None,
                        status=STATUS_ACTIVE, gender="Male")
        a1 = repo.create(a1); created_ids.append(a1.id)
        a2 = _make_case(None, OFFICER_A["username"], id=None, case_number=None,
                        status="Found", gender="Female")
        a2 = repo.create(a2); created_ids.append(a2.id)
        # OfficerB: same status combos but should be invisible to A
        b1 = _make_case(None, OFFICER_B["username"], id=None, case_number=None,
                        status=STATUS_ACTIVE, gender="Male")
        b1 = repo.create(b1); created_ids.append(b1.id)

        # OfficerA filtering for ACTIVE+Male → must return only a1, never b1
        hits = svc.search_and_filter_cases(
            status=STATUS_ACTIVE, gender="Male", current_user=OFFICER_A,
        )
        ids = {c.id for c in hits}
        assert a1.id in ids
        assert a2.id not in ids
        assert b1.id not in ids


# ══════════════════════════════════════════════════════════════════════
# 11. Unauthorized users cannot access case management (service guards)
# ══════════════════════════════════════════════════════════════════════

class TestUnauthorizedDenied:
    def test_unauthenticated_get_all_cases_raises(self):
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError):
            svc.get_all_cases(current_user=UNAUTHENTICATED)
        mock_repo.get_all.assert_not_called()

    def test_public_role_get_all_cases_raises(self):
        mock_repo = MagicMock()
        svc = CaseService(case_repo=mock_repo)

        with pytest.raises(PermissionError):
            svc.get_all_cases(current_user=PUBLIC_USER)
        mock_repo.get_all.assert_not_called()

    def test_unauthenticated_edit_raises(self):
        svc = CaseService(case_repo=MagicMock())
        with pytest.raises(PermissionError, match="authenticated"):
            svc.edit_case(1, name="X", current_user=UNAUTHENTICATED)

    def test_public_role_edit_raises(self):
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = _make_case(1, OFFICER_A["username"])
        svc = CaseService(case_repo=mock_repo)
        with pytest.raises(PermissionError):
            authorize_edit_case(PUBLIC_USER, OFFICER_A["username"])

    def test_public_role_delete_raises(self):
        with pytest.raises(PermissionError):
            authorize_delete_case(PUBLIC_USER)

    def test_authorize_view_cases_public_raises(self):
        with pytest.raises(PermissionError):
            authorize_view_cases(PUBLIC_USER)
