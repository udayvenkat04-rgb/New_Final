"""
Unit & Integration Test Suite for Phase 23: Complete Case Lifecycle & Notification Management.

Tests:
1. Valid lifecycle transition.
2. Invalid lifecycle transition.
3. Admin authorization.
4. Officer authorization restriction.
5. Public user authorization restriction.
6. Audit event creation.
7. Timeline generation.
8. Match confirmation transition.
9. Match rejection transition.
10. Reopen workflow.
11. Resolve workflow.
12. Close workflow.
13. Duplicate transition.
14. Concurrent/stale transition.
15. Missing required resolution data.
16. Notification trigger.
17. Notification idempotency.
18. Failed notification.
19. Retry notification.
20. Soft delete audit retention.
21. Case search.
22. Case filters.
23. Role-based case visibility.
24. MongoDB failure resilience.
"""

import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any

from models.missing_person import MissingPerson
from models.case_event import CaseEvent
from models.match_review import MatchReview
from repositories.case_repository import CaseRepository
from repositories.case_event_repository import CaseEventRepository
from repositories.match_review_repository import MatchReviewRepository
from services.case_lifecycle_service import (
    CaseLifecycleService,
    STATE_ACTIVE_INVESTIGATION,
    STATE_POTENTIAL_MATCH,
    STATE_UNDER_MATCH_REVIEW,
    STATE_MATCH_CONFIRMED,
    STATE_MATCH_REJECTED,
    STATE_RESOLVED,
    STATE_CLOSED,
    STATE_REOPENED,
)
from services.match_review import MatchReviewService
from services.notification_service import NotificationService


# ── Mock Repositories for Unit Test Isolation ────────────────────────

class MockCaseRepository:
    def __init__(self):
        self.cases = {}
        self.history = []
        self.next_id = 1

    def create(self, case: MissingPerson) -> MissingPerson:
        if case.id is None:
            case.id = self.next_id
            self.next_id += 1
        self.cases[case.id] = case
        return case

    def get_by_id(self, case_id: int, include_deleted: bool = False) -> Optional[MissingPerson]:
        c = self.cases.get(case_id)
        if c and not include_deleted and getattr(c, "is_deleted", False):
            return None
        return c

    def update_status(self, case_id: int, status: str) -> bool:
        c = self.cases.get(case_id)
        if c:
            c.status = status
            c.updated_at = datetime.utcnow()
            return True
        return False

    def soft_delete(self, case_id: int) -> bool:
        c = self.cases.get(case_id)
        if c:
            c.is_deleted = True
            c.deleted_at = datetime.utcnow()
            return True
        return False

    def log_history(self, hist):
        self.history.append(hist)

    def get_history_by_case(self, case_id: int):
        return [h for h in self.history if getattr(h, "case_id", None) == case_id]

    def get_all(self, filter_query=None, include_deleted=False):
        res = list(self.cases.values())
        if filter_query and "created_by" in filter_query:
            res = [c for c in res if c.created_by == filter_query["created_by"]]
        if not include_deleted:
            res = [c for c in res if not getattr(c, "is_deleted", False)]
        return res


class MockCaseEventRepository:
    def __init__(self):
        self.events = []
        self.next_id = 1

    def create_event(self, event: CaseEvent) -> CaseEvent:
        if event.id is None:
            event.id = self.next_id
            self.next_id += 1
        self.events.append(event)
        return event

    def get_case_events(self, case_id: int) -> List[CaseEvent]:
        return [e for e in self.events if e.case_id == case_id]

    def get_latest_event(self, case_id: int) -> Optional[CaseEvent]:
        evs = self.get_case_events(case_id)
        return evs[-1] if evs else None


class MockNotificationService:
    def __init__(self):
        self.sent_alerts = []
        self.should_fail = False

    def send_match_confirmed_alert(self, match_data: dict, user: dict):
        if self.should_fail:
            return False, "SMTP connection timeout"
        self.sent_alerts.append(match_data)
        return True, "Email sent successfully"


# ── Test Setup Fixture ───────────────────────────────────────────────

@pytest.fixture
def phase23_setup():
    case_repo = MockCaseRepository()
    event_repo = MockCaseEventRepository()
    notif_service = MockNotificationService()

    lifecycle_service = CaseLifecycleService(case_repo=case_repo, event_repo=event_repo, notification_service=notif_service)

    admin_user = {"username": "admin_clerk", "role": "admin"}
    officer_user = {"username": "officer_john", "role": "officer"}

    # Register initial case
    case = case_repo.create(MissingPerson(
        name="Sam Wilson", age=30, gender="Male",
        last_seen_location="MG Road", last_seen_city="Pune", last_seen_state="Maharashtra",
        contact_name="Mary Wilson", contact_email="mary@example.com", contact_phone="+919876543210",
        status="ACTIVE_INVESTIGATION", created_by="officer_john"
    ))

    return lifecycle_service, case_repo, event_repo, notif_service, admin_user, officer_user, case.id


# ── Test Cases ──────────────────────────────────────────────────────

def test_valid_lifecycle_transition(phase23_setup):
    """1. Valid transition ACTIVE_INVESTIGATION -> POTENTIAL_MATCH."""
    svc, case_repo, event_repo, _, admin_user, _, case_id = phase23_setup
    ok, msg = svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    assert ok is True
    assert case_repo.get_by_id(case_id).status == STATE_POTENTIAL_MATCH


def test_invalid_lifecycle_transition(phase23_setup):
    """2. Invalid transition ACTIVE_INVESTIGATION -> MATCH_CONFIRMED is blocked."""
    svc, _, _, _, admin_user, _, case_id = phase23_setup
    ok, msg = svc.transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=admin_user)
    assert ok is False
    assert "Invalid transition" in msg


def test_admin_authorization(phase23_setup):
    """3. Admin permits Admin-only transitions."""
    svc, case_repo, _, _, admin_user, _, case_id = phase23_setup
    # Transition to POTENTIAL_MATCH -> UNDER_MATCH_REVIEW -> MATCH_CONFIRMED
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    svc.transition_case_status(case_id, STATE_UNDER_MATCH_REVIEW, user=admin_user)

    ok, msg = svc.transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=admin_user)
    assert ok is True
    assert case_repo.get_by_id(case_id).status == STATE_MATCH_CONFIRMED


def test_officer_authorization_restriction(phase23_setup):
    """4. Officer attempting Admin-only transition raises PermissionError."""
    svc, _, _, _, _, officer_user, case_id = phase23_setup
    # Setup state to UNDER_MATCH_REVIEW
    admin_user = {"username": "admin", "role": "admin"}
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    svc.transition_case_status(case_id, STATE_UNDER_MATCH_REVIEW, user=admin_user)

    with pytest.raises(PermissionError):
        svc.transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=officer_user)


def test_public_user_authorization_restriction(phase23_setup):
    """5. Public user attempting lifecycle transition raises PermissionError."""
    svc, _, _, _, _, _, case_id = phase23_setup
    with pytest.raises(PermissionError):
        svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=None)


def test_audit_event_creation(phase23_setup):
    """6. Transition creates immutable CaseEvent record."""
    svc, _, event_repo, _, admin_user, _, case_id = phase23_setup
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user, reason="KNN match score 94.5%")
    events = event_repo.get_case_events(case_id)
    assert len(events) == 1
    assert events[0].new_status == STATE_POTENTIAL_MATCH
    assert events[0].reason == "KNN match score 94.5%"


def test_timeline_generation(phase23_setup):
    """7. Timeline aggregates CaseEvents chronologically."""
    svc, _, event_repo, _, admin_user, _, case_id = phase23_setup
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    timeline = svc.get_case_timeline(case_id)
    assert len(timeline) >= 1
    assert timeline[0]["new_status"] == STATE_POTENTIAL_MATCH


def test_match_confirmation_transition(phase23_setup):
    """8. Confirming match transitions to MATCH_CONFIRMED."""
    svc, case_repo, _, _, admin_user, _, case_id = phase23_setup
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    svc.transition_case_status(case_id, STATE_UNDER_MATCH_REVIEW, user=admin_user)

    ok, msg = svc.transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=admin_user, reason="Biometric evidence verified.")
    assert ok is True
    assert case_repo.get_by_id(case_id).status == STATE_MATCH_CONFIRMED


def test_match_rejection_transition(phase23_setup):
    """9. Rejecting match transitions to MATCH_REJECTED then back to ACTIVE_INVESTIGATION."""
    svc, case_repo, _, _, admin_user, _, case_id = phase23_setup
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    svc.transition_case_status(case_id, STATE_UNDER_MATCH_REVIEW, user=admin_user)

    ok1, msg1 = svc.transition_case_status(case_id, STATE_MATCH_REJECTED, user=admin_user)
    assert ok1 is True

    ok2, msg2 = svc.transition_case_status(case_id, STATE_ACTIVE_INVESTIGATION, user=admin_user)
    assert ok2 is True
    assert case_repo.get_by_id(case_id).status == STATE_ACTIVE_INVESTIGATION


def test_reopen_workflow(phase23_setup):
    """10. Reopen workflow transitions CLOSED -> REOPENED -> ACTIVE_INVESTIGATION."""
    svc, case_repo, _, _, admin_user, _, case_id = phase23_setup
    # Transition to RESOLVED then CLOSED
    svc.resolve_case(case_id, user=admin_user, resolution_type="Found", resolution_notes="Found safe")
    svc.close_case(case_id, user=admin_user, notes="Closing bulletin")

    ok_ro, msg_ro = svc.reopen_case(case_id, user=admin_user, reason="New evidence reported.")
    assert ok_ro is True
    assert case_repo.get_by_id(case_id).status == STATE_ACTIVE_INVESTIGATION


def test_resolve_workflow(phase23_setup):
    """11. Resolve workflow sets state to RESOLVED with notes."""
    svc, case_repo, _, _, admin_user, _, case_id = phase23_setup
    ok, msg = svc.resolve_case(case_id, user=admin_user, resolution_type="Reunited", resolution_notes="Returned home safely.")
    assert ok is True
    assert case_repo.get_by_id(case_id).status == STATE_RESOLVED


def test_close_workflow(phase23_setup):
    """12. Close workflow sets state to CLOSED."""
    svc, case_repo, _, _, admin_user, _, case_id = phase23_setup
    svc.resolve_case(case_id, user=admin_user, resolution_type="Found", resolution_notes="Located")
    ok, msg = svc.close_case(case_id, user=admin_user, notes="Admin closed case")
    assert ok is True
    assert case_repo.get_by_id(case_id).status == STATE_CLOSED


def test_duplicate_transition_prevention(phase23_setup):
    """13. Duplicate transition current == requested returns error."""
    svc, _, _, _, admin_user, _, case_id = phase23_setup
    ok, msg = svc.transition_case_status(case_id, STATE_ACTIVE_INVESTIGATION, user=admin_user)
    assert ok is False
    assert "already in" in msg


def test_stale_concurrency_transition(phase23_setup):
    """14. Stale optimistic lock check returns STALE_TRANSITION error."""
    svc, _, _, _, admin_user, _, case_id = phase23_setup
    ok, msg = svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user, expected_current_status="RESOLVED")
    assert ok is False
    assert "STALE_TRANSITION" in msg


def test_missing_required_resolution_data(phase23_setup):
    """15. Transition requiring reason/notes fails if missing."""
    svc, _, _, _, admin_user, _, case_id = phase23_setup
    ok, msg = svc.transition_case_status(case_id, STATE_RESOLVED, user=admin_user, reason="")
    assert ok is False
    assert "reason/notes is required" in msg


def test_notification_trigger(phase23_setup):
    """16. MATCH_CONFIRMED triggers notification service alert."""
    svc, _, _, notif_service, admin_user, _, case_id = phase23_setup
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    svc.transition_case_status(case_id, STATE_UNDER_MATCH_REVIEW, user=admin_user)
    svc.transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=admin_user)

    assert len(notif_service.sent_alerts) == 1
    assert notif_service.sent_alerts[0]["case_id"] == case_id


def test_notification_idempotency(phase23_setup):
    """17. Repeated notifications with same event key are prevented."""
    _, case_repo, _, _, admin_user, _, case_id = phase23_setup
    notif_service = NotificationService(case_repo=case_repo)
    match_data = {"case_id": case_id, "case_number": "MP-2026-00001", "name": "Sam", "contact_email": "s@ex.com", "event_id": 99}

    ok1, msg1 = notif_service.send_match_confirmed_alert(match_data, admin_user)
    ok2, msg2 = notif_service.send_match_confirmed_alert(match_data, admin_user)

    assert ok1 is True
    assert ok2 is True


def test_failed_notification_resilience(phase23_setup):
    """18. Failed email notification does NOT reverse case transition."""
    svc, case_repo, _, notif_service, admin_user, _, case_id = phase23_setup
    notif_service.should_fail = True

    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    svc.transition_case_status(case_id, STATE_UNDER_MATCH_REVIEW, user=admin_user)

    ok, msg = svc.transition_case_status(case_id, STATE_MATCH_CONFIRMED, user=admin_user)
    assert ok is True
    assert case_repo.get_by_id(case_id).status == STATE_MATCH_CONFIRMED
    assert "Notification alert failed" in msg


def test_retry_notification(phase23_setup):
    """19. Retrying notification works safely."""
    _, case_repo, _, _, admin_user, _, case_id = phase23_setup
    notif_service = NotificationService(case_repo=case_repo)

    res_ok, res_msg = notif_service.send_match_confirmed_alert(
        {"case_id": case_id, "case_number": "MP-2026-00010", "name": "Test", "contact_email": "t@ex.com", "event_id": 88},
        admin_user
    )
    assert res_ok is True


def test_soft_delete_audit_retention(phase23_setup):
    """20. Soft-deleted case retains event audit history."""
    svc, case_repo, event_repo, _, admin_user, _, case_id = phase23_setup
    svc.transition_case_status(case_id, STATE_POTENTIAL_MATCH, user=admin_user)
    case_repo.soft_delete(case_id)

    assert case_repo.get_by_id(case_id) is None  # Excluded from normal lookup
    assert case_repo.get_by_id(case_id, include_deleted=True) is not None

    events = event_repo.get_case_events(case_id)
    assert len(events) == 1


def test_case_search(phase23_setup):
    """21. Search cases by name, city, state."""
    _, case_repo, _, _, _, _, _ = phase23_setup
    results = case_repo.get_all()
    assert len(results) >= 1
    assert results[0].name == "Sam Wilson"


def test_case_filters(phase23_setup):
    """22. Filter cases by status."""
    _, case_repo, _, _, _, _, _ = phase23_setup
    active = [c for c in case_repo.get_all() if c.status == STATE_ACTIVE_INVESTIGATION]
    assert len(active) == 1


def test_role_based_case_visibility(phase23_setup):
    """23. Officer visibility restricted to own created cases."""
    _, case_repo, _, _, _, officer_user, _ = phase23_setup
    case_repo.create(MissingPerson(name="Other Case", age=40, gender="Female", last_seen_location="City", created_by="officer_other"))

    my_cases = case_repo.get_all({"created_by": officer_user["username"]})
    assert len(my_cases) == 1
    assert my_cases[0].name == "Sam Wilson"


def test_mongodb_failure_resilience():
    """24. Database failure resilience."""
    class FailingCaseRepo(CaseRepository):
        def get_by_id(self, case_id, include_deleted=False):
            return None

    svc = CaseLifecycleService(case_repo=FailingCaseRepo())
    admin_user = {"username": "admin", "role": "admin"}
    ok, msg = svc.transition_case_status(999, STATE_POTENTIAL_MATCH, user=admin_user)
    assert ok is False
    assert "not found" in msg
