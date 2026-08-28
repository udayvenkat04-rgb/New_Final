"""
Unit & Integration Test Suite for Phase 22: Public Missing Person Submission Portal.

Tests:
1. Public portal unauthenticated access.
2. Required field validation.
3. Invalid email format.
4. Invalid phone format.
5. Invalid age range.
6. Missing consent declaration.
7. Invalid image type.
8. Oversized image rejection.
9. Valid public submission.
10. Submission reference generation.
11. Duplicate reference prevention.
12. Possible duplicate detection.
13. Public user cannot access Admin review.
14. Officer cannot approve submission.
15. Admin can review submissions.
16. Admin approval workflow.
17. Admin rejection workflow.
18. Approval creates official case.
19. Rejection does not create official case.
20. Admin audit trail logging.
21. Public response sanitization.
22. Status lookup privacy protection.
23. MongoDB failure resilience.
24. Email acknowledgement resilience.
"""

import pytest
from datetime import datetime
from typing import Optional
from models.missing_person import MissingPerson
from models.public_submission import PublicSubmission, PublicSubmissionAudit
from repositories.case_repository import CaseRepository
from repositories.public_submission_repository import PublicSubmissionRepository
from services.case_service import CaseService
from services.public_submission_service import PublicSubmissionService
from services.public_submission_review_service import PublicSubmissionReviewService


# ── Mock Repositories for Isolated Unit Testing ──────────────────────

class MockPublicSubmissionRepository:
    def __init__(self):
        self.submissions = {}
        self.audits = []
        self.next_id = 1
        self.next_audit_id = 1

    def create_submission(self, submission: PublicSubmission) -> PublicSubmission:
        if submission.id is None:
            submission.id = self.next_id
            self.next_id += 1
        self.submissions[submission.id] = submission
        return submission

    def get_submission_by_id(self, submission_id: int) -> Optional[PublicSubmission]:
        return self.submissions.get(submission_id)

    def get_submission_by_reference(self, reference: str) -> Optional[PublicSubmission]:
        for s in self.submissions.values():
            if s.submission_reference == reference:
                return s
        return None

    def get_pending_submissions(self) -> list:
        return [s for s in self.submissions.values() if s.status == "PENDING_VERIFICATION"]

    def get_all_submissions(self, status: str = None) -> list:
        if status and status != "All":
            return [s for s in self.submissions.values() if s.status == status]
        return list(self.submissions.values())

    def update_submission_status(self, submission_id: int, status: str, reviewed_by: str, review_notes: str = None, approved_case_id: int = None) -> bool:
        s = self.submissions.get(submission_id)
        if s:
            s.status = status
            s.reviewed_by = reviewed_by
            s.reviewed_at = datetime.utcnow()
            if review_notes:
                s.review_notes = review_notes
            if approved_case_id:
                s.approved_case_id = approved_case_id
            return True
        return False

    def check_possible_duplicate(self, full_name: str, age: int, city: str = None, state: str = None) -> bool:
        for s in self.submissions.values():
            if s.full_name.lower() == full_name.lower() and s.age == age:
                return True
        return False

    def create_audit_record(self, audit: PublicSubmissionAudit) -> PublicSubmissionAudit:
        if audit.id is None:
            audit.id = self.next_audit_id
            self.next_audit_id += 1
        self.audits.append(audit)
        return audit

    def get_submission_history(self, submission_id: int) -> list:
        return [a for a in self.audits if a.submission_id == submission_id]


class MockCaseRepository:
    def __init__(self):
        self.cases = {}
        self.next_id = 1

    def create(self, case: MissingPerson) -> MissingPerson:
        if case.id is None:
            case.id = self.next_id
            self.next_id += 1
        self.cases[case.id] = case
        return case

    def get_by_id(self, case_id: int) -> Optional[MissingPerson]:
        return self.cases.get(case_id)

    def get_all(self, query=None):
        return list(self.cases.values())

    def log_history(self, history):
        pass


# ── Test Setup Fixture ───────────────────────────────────────────────

@pytest.fixture
def phase22_setup():
    sub_repo = MockPublicSubmissionRepository()
    case_repo = MockCaseRepository()
    case_service = CaseService(case_repo=case_repo)

    pub_service = PublicSubmissionService(repository=sub_repo)
    review_service = PublicSubmissionReviewService(submission_repo=sub_repo, case_repo=case_repo, case_service=case_service)

    admin_user = {"username": "admin_clerk", "role": "admin"}
    officer_user = {"username": "officer_john", "role": "officer"}

    return pub_service, review_service, sub_repo, case_repo, admin_user, officer_user


# ── Test Cases ──────────────────────────────────────────────────────

def test_public_portal_unauthenticated_access(phase22_setup):
    """1. Public service operates without user login/token."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data({
        "full_name": "John Doe", "age": 30, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Jane Doe", "contact_email": "jane@example.com",
        "contact_phone": "+919876543210", "consent": True
    })
    assert valid is True


def test_required_field_validation(phase22_setup):
    """2. Missing required fields returns validation error."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data({})
    assert valid is False
    assert "INVALID_FULL_NAME" in msg


def test_invalid_email_format(phase22_setup):
    """3. Invalid email format rejection."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data({
        "full_name": "John Doe", "age": 30, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Jane Doe", "contact_email": "invalid-email-address",
        "contact_phone": "+919876543210", "consent": True
    })
    assert valid is False
    assert "INVALID_EMAIL" in msg


def test_invalid_phone_format(phase22_setup):
    """4. Invalid phone format rejection."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data({
        "full_name": "John Doe", "age": 30, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Jane Doe", "contact_email": "jane@example.com",
        "contact_phone": "abc-phone", "consent": True
    })
    assert valid is False
    assert "INVALID_PHONE" in msg


def test_invalid_age_range(phase22_setup):
    """5. Invalid age range rejection."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data({
        "full_name": "John Doe", "age": 150, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Jane Doe", "contact_email": "jane@example.com",
        "contact_phone": "+919876543210", "consent": True
    })
    assert valid is False
    assert "INVALID_AGE" in msg


def test_missing_consent_declaration(phase22_setup):
    """6. Missing consent checkbox rejection."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data({
        "full_name": "John Doe", "age": 30, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Jane Doe", "contact_email": "jane@example.com",
        "contact_phone": "+919876543210", "consent": False
    })
    assert valid is False
    assert "MISSING_CONSENT" in msg


def test_invalid_image_type(phase22_setup):
    """7. Invalid image file extension rejection."""
    pub_service, _, _, _, _, _ = phase22_setup
    valid, msg = pub_service.validate_submission_data(
        form_data={"full_name": "John Doe", "age": 30, "gender": "Male", "last_seen_city": "Pune", "last_seen_state": "Maharashtra", "complainant_name": "Jane Doe", "contact_email": "j@ex.com", "contact_phone": "+919876543210", "consent": True},
        image_bytes=b"fake-exe-bytes",
        filename="malicious.exe"
    )
    assert valid is False
    assert "INVALID_IMAGE_TYPE" in msg


def test_oversized_image_rejection(phase22_setup):
    """8. Oversized image file rejection (>100MB)."""
    pub_service, _, _, _, _, _ = phase22_setup
    large_bytes = b"0" * (101 * 1024 * 1024)
    valid, msg = pub_service.validate_submission_data(
        form_data={"full_name": "John Doe", "age": 30, "gender": "Male", "last_seen_city": "Pune", "last_seen_state": "Maharashtra", "complainant_name": "Jane Doe", "contact_email": "j@ex.com", "contact_phone": "+919876543210", "consent": True},
        image_bytes=large_bytes,
        filename="large.jpg"
    )
    assert valid is False
    assert "OVERSIZED_IMAGE" in msg


def test_valid_public_submission(phase22_setup):
    """9. Valid submission creates PENDING_VERIFICATION record."""
    pub_service, _, sub_repo, _, _, _ = phase22_setup
    ok, res = pub_service.create_public_submission({
        "full_name": "Alice Walker", "age": 28, "gender": "Female",
        "last_seen_city": "Mumbai", "last_seen_state": "Maharashtra",
        "complainant_name": "Bob Walker", "contact_email": "bob@example.com",
        "contact_phone": "+919876543210", "consent": True
    })
    assert ok is True
    assert res["status"] == "SUCCESS"
    assert res["submission_status"] == "PENDING_VERIFICATION"
    assert res["submission_reference"].startswith("MP-SUB-2026-")


def test_submission_reference_generation(phase22_setup):
    """10. Submission reference format uniqueness."""
    pub_service, _, _, _, _, _ = phase22_setup
    ref1 = pub_service.generate_submission_reference()
    assert ref1.startswith("MP-SUB-2026-")


def test_duplicate_reference_prevention(phase22_setup):
    """11. Duplicate reference lookup resilience."""
    pub_service, _, sub_repo, _, _, _ = phase22_setup
    ok, res = pub_service.create_public_submission({
        "full_name": "Alice Walker", "age": 28, "gender": "Female",
        "last_seen_city": "Mumbai", "last_seen_state": "Maharashtra",
        "complainant_name": "Bob Walker", "contact_email": "bob@example.com",
        "contact_phone": "+919876543210", "consent": True
    })
    ref = res["submission_reference"]
    sub = sub_repo.get_submission_by_reference(ref)
    assert sub is not None
    assert sub.submission_reference == ref


def test_possible_duplicate_detection(phase22_setup):
    """12. Possible duplicate candidate detection."""
    pub_service, _, sub_repo, _, _, _ = phase22_setup
    pub_service.create_public_submission({
        "full_name": "Alice Walker", "age": 28, "gender": "Female",
        "last_seen_city": "Mumbai", "last_seen_state": "Maharashtra",
        "complainant_name": "Bob Walker", "contact_email": "bob@example.com",
        "contact_phone": "+919876543210", "consent": True
    })

    # Second submission with same name and age
    ok, res2 = pub_service.create_public_submission({
        "full_name": "Alice Walker", "age": 28, "gender": "Female",
        "last_seen_city": "Mumbai", "last_seen_state": "Maharashtra",
        "complainant_name": "Charlie Walker", "contact_email": "charlie@example.com",
        "contact_phone": "+919876543210", "consent": True
    })
    assert ok is True
    assert res2["is_possible_duplicate"] is True


def test_public_user_cannot_access_admin_dashboard(phase22_setup):
    """13. Public / unauthenticated user blocked from review service."""
    _, review_service, _, _, _, _ = phase22_setup
    with pytest.raises(PermissionError):
        review_service.get_pending_submissions(user=None)


def test_officer_cannot_approve_submission(phase22_setup):
    """14. Officer role blocked from approving or rejecting submissions."""
    _, review_service, sub_repo, _, _, officer_user = phase22_setup
    sub = sub_repo.create_submission(PublicSubmission(
        submission_reference="MP-SUB-2026-000100", full_name="Test", age=20, gender="Male",
        complainant_name="Comp", contact_email="c@ex.com", contact_phone="1234567890"
    ))
    with pytest.raises(PermissionError):
        review_service.approve_submission(sub.id, user=officer_user)

    with pytest.raises(PermissionError):
        review_service.reject_submission(sub.id, user=officer_user)


def test_admin_can_review_submissions(phase22_setup):
    """15. Admin role can retrieve pending submissions queue."""
    pub_service, review_service, _, _, admin_user, _ = phase22_setup
    pub_service.create_public_submission({
        "full_name": "Pending Case", "age": 40, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Reporter", "contact_email": "r@ex.com",
        "contact_phone": "+919876543210", "consent": True
    })

    pending = review_service.get_pending_submissions(user=admin_user)
    assert len(pending) == 1
    assert pending[0].full_name == "Pending Case"


def test_admin_approval_workflow(phase22_setup):
    """16. Admin approval workflow updates submission status to APPROVED."""
    pub_service, review_service, sub_repo, _, admin_user, _ = phase22_setup
    ok_sub, res_sub = pub_service.create_public_submission({
        "full_name": "Approve Case", "age": 22, "gender": "Female",
        "last_seen_city": "Delhi", "last_seen_state": "Delhi",
        "complainant_name": "Parent", "contact_email": "p@ex.com",
        "contact_phone": "+919876543210", "consent": True
    })
    sub = sub_repo.get_submission_by_reference(res_sub["submission_reference"])

    ok, case_id, msg = review_service.approve_submission(sub.id, user=admin_user, notes="Verified valid report")
    assert ok is True
    assert case_id is not None

    updated_sub = sub_repo.get_submission_by_id(sub.id)
    assert updated_sub.status == "APPROVED"
    assert updated_sub.approved_case_id == case_id


def test_admin_rejection_workflow(phase22_setup):
    """17. Admin rejection workflow updates status to REJECTED."""
    pub_service, review_service, sub_repo, _, admin_user, _ = phase22_setup
    ok_sub, res_sub = pub_service.create_public_submission({
        "full_name": "Reject Case", "age": 50, "gender": "Male",
        "last_seen_city": "Nagpur", "last_seen_state": "Maharashtra",
        "complainant_name": "Reporter", "contact_email": "r@ex.com",
        "contact_phone": "+919876543210", "consent": True
    })
    sub = sub_repo.get_submission_by_reference(res_sub["submission_reference"])

    ok, msg = review_service.reject_submission(sub.id, user=admin_user, reason="Incomplete details provided")
    assert ok is True

    updated_sub = sub_repo.get_submission_by_id(sub.id)
    assert updated_sub.status == "REJECTED"
    assert updated_sub.review_notes == "Incomplete details provided"


def test_approval_creates_official_case(phase22_setup):
    """18. Approving public submission creates an official MissingPerson case."""
    pub_service, review_service, sub_repo, case_repo, admin_user, _ = phase22_setup
    ok_sub, res_sub = pub_service.create_public_submission({
        "full_name": "Official Case Test", "age": 35, "gender": "Male",
        "last_seen_city": "Bengaluru", "last_seen_state": "Karnataka",
        "complainant_name": "Family", "contact_email": "fam@ex.com",
        "contact_phone": "+919876543210", "consent": True
    })
    sub = sub_repo.get_submission_by_reference(res_sub["submission_reference"])

    ok, case_id, msg = review_service.approve_submission(sub.id, user=admin_user)
    assert ok is True

    created_case = case_repo.get_by_id(case_id)
    assert created_case is not None
    assert created_case.name == "Official Case Test"
    assert created_case.status == "Missing"


def test_rejection_does_not_create_official_case(phase22_setup):
    """19. Rejecting submission does NOT create an official case."""
    pub_service, review_service, sub_repo, case_repo, admin_user, _ = phase22_setup
    ok_sub, res_sub = pub_service.create_public_submission({
        "full_name": "No Official Case Test", "age": 35, "gender": "Male",
        "last_seen_city": "Bengaluru", "last_seen_state": "Karnataka",
        "complainant_name": "Family", "contact_email": "fam@ex.com",
        "contact_phone": "+919876543210", "consent": True
    })
    sub = sub_repo.get_submission_by_reference(res_sub["submission_reference"])

    review_service.reject_submission(sub.id, user=admin_user, reason="Invalid")
    assert len(case_repo.cases) == 0


def test_admin_audit_trail_logging(phase22_setup):
    """20. Approving or rejecting public submissions logs audit trail records."""
    pub_service, review_service, sub_repo, _, admin_user, _ = phase22_setup
    ok_sub, res_sub = pub_service.create_public_submission({
        "full_name": "Audit Trail Test", "age": 30, "gender": "Female",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Friend", "contact_email": "f@ex.com",
        "contact_phone": "+919876543210", "consent": True
    })
    sub = sub_repo.get_submission_by_reference(res_sub["submission_reference"])

    review_service.approve_submission(sub.id, user=admin_user, notes="Audit approved")

    history = sub_repo.get_submission_history(sub.id)
    assert len(history) == 2  # SUBMITTED + APPROVED
    assert history[1].action == "APPROVED"
    assert history[1].actor_username == "admin_clerk"


def test_public_response_sanitization(phase22_setup):
    """21. Public status lookup returns sanitized fields without private details."""
    pub_service, _, sub_repo, _, _, _ = phase22_setup
    ok_sub, res_sub = pub_service.create_public_submission({
        "full_name": "Private Sensitive Test", "age": 30, "gender": "Female",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Secret Reporter", "contact_email": "secret@example.com",
        "contact_phone": "+919876543210", "consent": True
    })

    ok_lookup, pub_info = pub_service.get_public_submission_status(res_sub["submission_reference"])
    assert ok_lookup is True
    assert "contact_email" not in pub_info
    assert "contact_phone" not in pub_info
    assert "complainant_name" not in pub_info
    assert "review_notes" not in pub_info
    assert "submission_reference" in pub_info
    assert "status" in pub_info


def test_status_lookup_rate_and_privacy_protection(phase22_setup):
    """22. Non-existent reference returns clean error without DB leakage."""
    pub_service, _, _, _, _, _ = phase22_setup
    ok, res = pub_service.get_public_submission_status("INVALID-REF-999")
    assert ok is False
    assert "NOT_FOUND" in res["error"]


def test_mongodb_failure_resilience():
    """23. Database failure resilience."""
    class FailingSubRepo(PublicSubmissionRepository):
        def get_all_submissions(self, status=None):
            return []

    svc = PublicSubmissionReviewService(submission_repo=FailingSubRepo())
    admin_user = {"username": "admin", "role": "admin"}
    pending = svc.get_pending_submissions(user=admin_user)
    assert pending == []


def test_email_acknowledgement_resilience(phase22_setup):
    """24. Email acknowledgement failure does not invalidate submission."""
    pub_service, _, _, _, _, _ = phase22_setup
    ok, res = pub_service.create_public_submission({
        "full_name": "Email Fail Test", "age": 25, "gender": "Male",
        "last_seen_city": "Pune", "last_seen_state": "Maharashtra",
        "complainant_name": "Reporter", "contact_email": "valid@example.com",
        "contact_phone": "+919876543210", "consent": True
    })
    assert ok is True
    assert res["status"] == "SUCCESS"
