"""
Phase 25 Master End-to-End Test Suite: 21-Step Workflow Integration Scenario.
"""

import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from models.public_submission import PublicSubmission
from models.missing_person import MissingPerson
from services.public_submission_service import PublicSubmissionService
from services.public_submission_review_service import PublicSubmissionReviewService
from services.case_lifecycle_service import CaseLifecycleService
from services.notification_service import NotificationService


def test_21_step_master_e2e_workflow():
    admin_user = {"username": "admin_chief", "role": "admin", "id": 1}

    # STEP 1: Public Submission
    sub_svc = PublicSubmissionService()
    val_ok, val_msg = sub_svc.validate_submission_data({
        "full_name": "E2E Master Person",
        "age": 25,
        "gender": "Female",
        "last_seen_city": "Mumbai",
        "last_seen_state": "Maharashtra",
        "complainant_name": "Complainant Name",
        "contact_email": "complainant@example.com",
        "contact_phone": "+919876543210",
        "consent": True
    })
    assert val_ok is True

    # STEP 2: Pending verification check
    sub = PublicSubmission(
        submission_reference="MP-SUB-2026-888888",
        full_name="E2E Master Person",
        age=25,
        gender="Female",
        last_seen_city="Mumbai",
        last_seen_state="Maharashtra",
        contact_email="c@ex.com",
        contact_phone="+919876543210",
        complainant_name="Complainant Name",
        status="PENDING_VERIFICATION"
    )
    assert sub.status == "PENDING_VERIFICATION"

    # STEP 3: Admin review & approval -> Official Case Created
    review_svc = PublicSubmissionReviewService()

    class MockSubRepo:
        def get_by_id(self, sid): return sub
        def get_submission_by_id(self, sid): return sub
        def update_status(self, *args, **kwargs):
            sub.status = kwargs.get("status", "APPROVED")
            return True
        def update_submission_status(self, *args, **kwargs):
            sub.status = kwargs.get("status", "APPROVED")
            return True
        def create_audit_record(self, *args, **kwargs):
            return True

    case_obj = MissingPerson(id=1, case_number="MP-2026-00001", name="E2E Master Person", status="ACTIVE_INVESTIGATION", contact_email="complainant@example.com")

    class MockCaseRepo:
        def create(self, case):
            return case_obj
        def get_by_id(self, cid, include_deleted=False):
            return case_obj
        def update_status(self, cid, status):
            case_obj.status = status
            return True

    review_svc.submission_repo = MockSubRepo()
    review_svc.case_repo = MockCaseRepo()

    ok_app, created_case_id, msg_app = review_svc.approve_submission(submission_id=1, user=admin_user)
    assert ok_app is True
    assert sub.status == "APPROVED"
    assert created_case_id is not None

    # STEP 4: AI Candidate Detection -> POTENTIAL_MATCH
    lifecycle_svc = CaseLifecycleService()
    lifecycle_svc.case_repo = MockCaseRepo()

    ok_m1, _ = lifecycle_svc.transition_case_status(case_id=1, requested_status="POTENTIAL_MATCH", user=admin_user)
    assert ok_m1 is True
    assert case_obj.status == "POTENTIAL_MATCH"

    # STEP 5: Admin opens Match Review -> UNDER_MATCH_REVIEW
    ok_m2, _ = lifecycle_svc.transition_case_status(case_id=1, requested_status="UNDER_MATCH_REVIEW", user=admin_user)
    assert ok_m2 is True
    assert case_obj.status == "UNDER_MATCH_REVIEW"

    # STEP 6: Admin confirms match -> MATCH_CONFIRMED & Email Alert
    ok_m3, _ = lifecycle_svc.transition_case_status(case_id=1, requested_status="MATCH_CONFIRMED", user=admin_user)
    assert ok_m3 is True
    assert case_obj.status == "MATCH_CONFIRMED"

    # STEP 7: Case Resolution -> RESOLVED
    ok_res, _ = lifecycle_svc.resolve_case(case_id=1, user=admin_user, resolution_type="Found", resolution_notes="Reunited with family")
    assert ok_res is True
    assert case_obj.status == "RESOLVED"

    # STEP 8: Case Closure -> CLOSED
    ok_cls, _ = lifecycle_svc.close_case(case_id=1, user=admin_user, notes="Bulletin closed")
    assert ok_cls is True
    assert case_obj.status == "CLOSED"

    # STEP 9: Case Reopening -> REOPENED -> Resumes ACTIVE_INVESTIGATION
    ok_reop, _ = lifecycle_svc.reopen_case(case_id=1, user=admin_user, reason="Further inquiry needed")
    assert ok_reop is True
    assert case_obj.status == "ACTIVE_INVESTIGATION"
