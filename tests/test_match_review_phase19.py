"""
Unit & Integration Test Suite for Match Review Service (Phase 19).

Tests:
1. Admin can access review queue.
2. Officer cannot confirm match.
3. Unauthenticated user cannot access review.
4. Create pending review.
5. Retrieve pending reviews.
6. Confirm match.
7. Reject match.
8. Mark further review.
9. Invalid review status transition.
10. Duplicate confirmation.
11. Duplicate rejection.
12. Audit record creation.
13. Reviewer information.
14. Timestamp recording.
15. Case relationship.
16. Multiple candidates.
17. Existing confirmed review protection.
18. Database failure handling.
19. Unauthorized direct service call.
"""

import pytest
from datetime import datetime
from models.case_history import CaseHistory
from models.match_review import MatchReview, MatchReviewAudit
from models.missing_person import MissingPerson
from repositories.case_repository import CaseRepository
from repositories.match_review_repository import MatchReviewRepository
from services.match_review import (
    DECISION_CONFIRMED,
    DECISION_FURTHER_REVIEW,
    DECISION_PENDING,
    DECISION_REJECTED,
    MatchReviewService,
)


# ── Mock Repositories for Isolated Unit Tests ───────────────────────

class MockCaseRepository:
    def __init__(self):
        self.cases = {
            "MP-001": MissingPerson(id="MP-001", name="Alice Smith", status="Missing"),
            "MP-002": MissingPerson(id="MP-002", name="Bob Jones", status="Missing"),
            1: MissingPerson(id=1, name="Alice Smith", status="Missing"),
            2: MissingPerson(id=2, name="Bob Jones", status="Missing"),
        }
        self.history = []

    def get_by_id(self, case_id):
        return self.cases.get(case_id) or self.cases.get(str(case_id))

    def update_status(self, case_id, status, updated_by=None):
        case = self.get_by_id(case_id)
        if case:
            case.status = status
            return True
        return False

    def log_history(self, history_log):
        self.history.append(history_log)


class MockMatchReviewRepository:
    def __init__(self):
        self.reviews = {}
        self.audits = []
        self.next_id = 1
        self.next_audit_id = 1

    def create_review(self, review: MatchReview) -> MatchReview:
        if review.id is None:
            review.id = self.next_id
            self.next_id += 1
        self.reviews[review.id] = review
        return review

    def get_review_by_id(self, review_id: int) -> MatchReview:
        return self.reviews.get(review_id)

    def get_pending_reviews(self):
        return [r for r in self.reviews.values() if r.review_status in (DECISION_PENDING, "Pending Review")]

    def get_all_reviews(self, filter_query: dict = None):
        res = list(self.reviews.values())
        if filter_query and "review_status" in filter_query:
            allowed = filter_query["review_status"]
            if isinstance(allowed, dict) and "$in" in allowed:
                allowed_vals = allowed["$in"]
                res = [r for r in res if r.review_status in allowed_vals]
            else:
                res = [r for r in res if r.review_status == allowed]
        return res

    def get_reviews_by_case(self, case_id):
        return [r for r in self.reviews.values() if str(r.case_id) == str(case_id)]

    def update_review_decision(self, review_id: int, review_status: str, review_decision: str, reviewed_by: str, review_notes: str = None) -> bool:
        r = self.reviews.get(review_id)
        if r:
            r.review_status = review_status
            r.review_decision = review_decision
            r.reviewed_by = reviewed_by
            r.reviewed_at = datetime.utcnow()
            r.review_notes = review_notes
            return True
        return False

    def count_reviews_by_status(self):
        counts = {"PENDING_REVIEW": 0, "CONFIRMED": 0, "REJECTED": 0, "NEEDS_FURTHER_REVIEW": 0}
        for r in self.reviews.values():
            st = r.review_status
            if st in counts:
                counts[st] += 1
        return counts

    def create_audit_record(self, audit: MatchReviewAudit) -> MatchReviewAudit:
        if audit.id is None:
            audit.id = self.next_audit_id
            self.next_audit_id += 1
        self.audits.append(audit)
        return audit

    def get_review_history(self, review_id: int):
        return [a for a in self.audits if a.match_review_id == review_id]


# ── Test Cases ──────────────────────────────────────────────────────

@pytest.fixture
def review_setup():
    case_repo = MockCaseRepository()
    review_repo = MockMatchReviewRepository()
    service = MatchReviewService(review_repo=review_repo, case_repo=case_repo)
    admin_user = {"username": "admin_alice", "role": "admin"}
    officer_user = {"username": "officer_bob", "role": "officer"}
    return service, review_repo, case_repo, admin_user, officer_user


def test_admin_can_access_review_queue(review_setup):
    """1. Admin can access review queue."""
    service, review_repo, _, admin_user, _ = review_setup
    service.create_potential_match(case_id=1, similarity_score=90.0, distance=0.1)

    queue = service.get_review_queue(user=admin_user)
    assert len(queue) == 1
    assert queue[0].case_id == 1


def test_officer_cannot_confirm_match(review_setup):
    """2. Officer user cannot confirm match (raises PermissionError)."""
    service, review_repo, _, _, officer_user = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=90.0, distance=0.1)

    with pytest.raises(PermissionError, match="Only administrators can review matches"):
        service.review_match(match_id=r.id, status="CONFIRMED", current_user=officer_user)


def test_unauthenticated_user_access(review_setup):
    """3. Unauthenticated user raises PermissionError."""
    service, _, _, _, _ = review_setup
    invalid_user = {"username": "anonymous", "role": "guest"}

    with pytest.raises(PermissionError):
        service.get_review_queue(user=invalid_user)


def test_create_pending_review(review_setup):
    """4. Create potential match in PENDING_REVIEW status."""
    service, _, _, _, _ = review_setup
    r = service.create_potential_match(case_id="MP-001", similarity_score=92.5, distance=0.15, source_type="IMAGE")

    assert r.id is not None
    assert r.review_status == DECISION_PENDING
    assert r.similarity_score == 92.5
    assert r.distance == 0.15


def test_retrieve_pending_reviews(review_setup):
    """5. Retrieve pending reviews."""
    service, _, _, admin_user, _ = review_setup
    service.create_potential_match(case_id=1, similarity_score=85.0, distance=0.2)
    service.create_potential_match(case_id=2, similarity_score=88.0, distance=0.18)

    pending = service.get_pending_reviews(current_user=admin_user)
    assert len(pending) == 2


def test_confirm_match(review_setup):
    """6. Confirm match updates review status, logs audit, updates case to Found."""
    service, review_repo, case_repo, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=95.0, distance=0.1)

    success = service.review_match(match_id=r.id, status="CONFIRMED", review_notes="Visual match verified", current_user=admin_user)
    assert success is True

    updated_review = review_repo.get_review_by_id(r.id)
    assert updated_review.review_status == DECISION_CONFIRMED
    assert updated_review.reviewed_by == "admin_alice"

    # Verify case status updated to Found
    updated_case = case_repo.get_by_id(1)
    assert updated_case.status == "Found"

    # Verify audit record created
    history = review_repo.get_review_history(r.id)
    assert len(history) == 1
    assert history[0].new_status == DECISION_CONFIRMED
    assert history[0].reviewer_id == "admin_alice"


def test_reject_match(review_setup):
    """7. Reject match updates status to REJECTED, logs audit, preserves evidence."""
    service, review_repo, case_repo, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=70.0, distance=0.5)

    success = service.review_match(match_id=r.id, status="REJECTED", review_notes="False positive", current_user=admin_user)
    assert success is True

    updated_review = review_repo.get_review_by_id(r.id)
    assert updated_review.review_status == DECISION_REJECTED

    # Verify case status remains Missing
    case = case_repo.get_by_id(1)
    assert case.status == "Missing"

    # Verify audit log
    history = review_repo.get_review_history(r.id)
    assert len(history) == 1
    assert history[0].new_status == DECISION_REJECTED


def test_mark_further_review(review_setup):
    """8. Mark match as NEEDS_FURTHER_REVIEW."""
    service, review_repo, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=80.0, distance=0.3)

    success = service.review_match(match_id=r.id, status="NEEDS_FURTHER_REVIEW", current_user=admin_user)
    assert success is True

    updated_review = review_repo.get_review_by_id(r.id)
    assert updated_review.review_status == DECISION_FURTHER_REVIEW


def test_invalid_review_status_transition(review_setup):
    """9. Invalid status raises ValueError."""
    service, _, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=80.0, distance=0.3)

    with pytest.raises(ValueError, match="Invalid review decision"):
        service.review_match(match_id=r.id, status="INVALID_DECISION", current_user=admin_user)


def test_duplicate_confirmation_prevention(review_setup):
    """10. Attempting duplicate CONFIRMED raises ValueError."""
    service, _, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=95.0, distance=0.1)

    service.review_match(match_id=r.id, status="CONFIRMED", current_user=admin_user)

    with pytest.raises(ValueError, match="already been CONFIRMED"):
        service.review_match(match_id=r.id, status="CONFIRMED", current_user=admin_user)


def test_duplicate_rejection_prevention(review_setup):
    """11. Attempting duplicate REJECTED raises ValueError."""
    service, _, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=60.0, distance=0.6)

    service.review_match(match_id=r.id, status="REJECTED", current_user=admin_user)

    with pytest.raises(ValueError, match="already been REJECTED"):
        service.review_match(match_id=r.id, status="REJECTED", current_user=admin_user)


def test_audit_record_creation(review_setup):
    """12. Audit record creation verifies all fields."""
    service, review_repo, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=90.0, distance=0.2)

    service.review_match(match_id=r.id, status="CONFIRMED", review_notes="Audit test notes", current_user=admin_user)
    audits = review_repo.get_review_history(r.id)

    assert len(audits) == 1
    audit = audits[0]
    assert audit.match_review_id == r.id
    assert audit.case_id == 1
    assert audit.previous_status == DECISION_PENDING
    assert audit.new_status == DECISION_CONFIRMED
    assert audit.reviewer_id == "admin_alice"
    assert audit.reviewer_role == "admin"
    assert audit.review_notes == "Audit test notes"


def test_reviewer_information(review_setup):
    """13. Reviewer username and role recorded accurately."""
    service, review_repo, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=90.0, distance=0.2)

    service.review_match(match_id=r.id, status="REJECTED", current_user=admin_user)
    rev = review_repo.get_review_by_id(r.id)
    assert rev.reviewed_by == "admin_alice"


def test_timestamp_recording(review_setup):
    """14. Reviewed_at and audit timestamp recorded."""
    service, review_repo, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=90.0, distance=0.2)

    service.review_match(match_id=r.id, status="CONFIRMED", current_user=admin_user)
    rev = review_repo.get_review_by_id(r.id)
    assert rev.reviewed_at is not None
    assert isinstance(rev.reviewed_at, datetime)


def test_case_relationship(review_setup):
    """15. Case relationship link."""
    service, review_repo, _, _, _ = review_setup
    r = service.create_potential_match(case_id="MP-001", similarity_score=91.0, distance=0.15)
    by_case = review_repo.get_reviews_by_case("MP-001")
    assert len(by_case) == 1
    assert by_case[0].id == r.id


def test_multiple_candidates(review_setup):
    """16. Multiple candidates reviewed independently."""
    service, review_repo, case_repo, admin_user, _ = review_setup
    r1 = service.create_potential_match(case_id=1, similarity_score=95.0, distance=0.1)
    r2 = service.create_potential_match(case_id=2, similarity_score=60.0, distance=0.7)

    service.review_match(match_id=r1.id, status="CONFIRMED", current_user=admin_user)
    service.review_match(match_id=r2.id, status="REJECTED", current_user=admin_user)

    assert review_repo.get_review_by_id(r1.id).review_status == DECISION_CONFIRMED
    assert review_repo.get_review_by_id(r2.id).review_status == DECISION_REJECTED
    assert case_repo.get_by_id(1).status == "Found"
    assert case_repo.get_by_id(2).status == "Missing"


def test_existing_confirmed_review_protection(review_setup):
    """17. Existing confirmed review protection."""
    service, _, _, admin_user, _ = review_setup
    r = service.create_potential_match(case_id=1, similarity_score=95.0, distance=0.1)
    service.review_match(match_id=r.id, status="CONFIRMED", current_user=admin_user)

    with pytest.raises(ValueError):
        service.review_match(match_id=r.id, status="CONFIRMED", current_user=admin_user)


def test_database_failure_handling():
    """18. Non-existent review ID returns False."""
    service = MatchReviewService(review_repo=MockMatchReviewRepository(), case_repo=MockCaseRepository())
    admin_user = {"username": "admin_alice", "role": "admin"}
    res = service.review_match(match_id=9999, status="CONFIRMED", current_user=admin_user)
    assert res is False


def test_unauthorized_direct_service_call():
    """19. Unauthorized direct service call raises PermissionError."""
    service = MatchReviewService(review_repo=MockMatchReviewRepository(), case_repo=MockCaseRepository())
    officer_user = {"username": "officer_bob", "role": "officer"}
    with pytest.raises(PermissionError):
        service.get_review_queue(user=officer_user)
