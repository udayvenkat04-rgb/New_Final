"""
Phase 25 Integration Test Suite: Services, Repositories, Lifecycle Transitions, RBAC Matrix.
"""

import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from models.missing_person import MissingPerson
from models.public_submission import PublicSubmission
from services.case_lifecycle_service import CaseLifecycleService
from services.public_submission_service import PublicSubmissionService
from services.public_submission_review_service import PublicSubmissionReviewService


def test_public_submission_flow():
    sub_svc = PublicSubmissionService()
    valid, msg = sub_svc.validate_submission_data({
        "full_name": "Integration Test Person",
        "age": 28,
        "gender": "Female",
        "last_seen_city": "Delhi",
        "last_seen_state": "Delhi",
        "complainant_name": "Complainant Name",
        "contact_email": "complainant@example.com",
        "contact_phone": "+919876543210",
        "consent": True
    })
    assert valid is True
    assert msg == "VALIDATION_SUCCESS"


def test_admin_public_submission_review_approval(monkeypatch):
    review_svc = PublicSubmissionReviewService()
    admin_user = {"username": "admin_chief", "role": "admin", "id": 1}

    mock_sub = PublicSubmission(
        submission_reference="MP-SUB-2026-999999",
        full_name="Approved Victim",
        age=32,
        gender="Male",
        last_seen_city="Delhi",
        last_seen_state="Delhi",
        contact_email="c@ex.com",
        contact_phone="+919876543210",
        complainant_name="Complainant Name",
        status="PENDING_VERIFICATION"
    )

    class MockSubRepo:
        def get_by_id(self, sid): return mock_sub
        def get_submission_by_id(self, sid): return mock_sub
        def update_status(self, *args, **kwargs):
            mock_sub.status = kwargs.get("status", "APPROVED")
            return True
        def update_submission_status(self, *args, **kwargs):
            mock_sub.status = kwargs.get("status", "APPROVED")
            return True
        def create_audit_record(self, *args, **kwargs):
            return True

    class MockCaseRepo:
        def create(self, case):
            case.id = 101
            return case

    review_svc.submission_repo = MockSubRepo()
    review_svc.case_repo = MockCaseRepo()

    ok, created_case_id, msg = review_svc.approve_submission(submission_id=1, user=admin_user, notes="Approved")
    assert ok is True
    assert created_case_id == 101
    assert mock_sub.status == "APPROVED"


def test_case_lifecycle_state_machine():
    lifecycle_svc = CaseLifecycleService()
    admin_user = {"username": "admin_chief", "role": "admin", "id": 1}
    officer_user = {"username": "officer_1", "role": "officer", "id": 2}

    mock_case = MissingPerson(id=1, case_number="MP-101", name="Lifecycle Test", status="ACTIVE_INVESTIGATION")

    class MockCaseRepo:
        def get_by_id(self, cid, include_deleted=False): return mock_case
        def update_status(self, cid, status):
            mock_case.status = status
            return True

    lifecycle_svc.case_repo = MockCaseRepo()

    # Move to POTENTIAL_MATCH
    ok1, _ = lifecycle_svc.transition_case_status(case_id=1, requested_status="POTENTIAL_MATCH", user=admin_user)
    assert ok1 is True
    assert mock_case.status == "POTENTIAL_MATCH"

    # Move to UNDER_MATCH_REVIEW
    ok2, _ = lifecycle_svc.transition_case_status(case_id=1, requested_status="UNDER_MATCH_REVIEW", user=admin_user)
    assert ok2 is True

    # Officer attempt to CONFIRM match -> raises PermissionError
    with pytest.raises(PermissionError):
        lifecycle_svc.transition_case_status(case_id=1, requested_status="MATCH_CONFIRMED", user=officer_user)

    # Admin confirms match
    ok3, _ = lifecycle_svc.transition_case_status(case_id=1, requested_status="MATCH_CONFIRMED", user=admin_user)
    assert ok3 is True
    assert mock_case.status == "MATCH_CONFIRMED"
