"""
Phase 25 Unit Test Suite: Data Models, Validators, and Security Functions.
"""

import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from models.missing_person import MissingPerson
from models.public_submission import PublicSubmission
from models.case_event import CaseEvent
from models.match_review import MatchReview
from models.notification import Notification
from utils.security import hash_password, verify_password
from utils.validators import validate_email, validate_phone, validate_image_filename


def test_missing_person_model_initialization():
    case = MissingPerson(
        case_number="MP-2026-00001",
        name="Test Person",
        age=30,
        gender="Male",
        last_seen_location="Delhi",
        created_by="officer_1"
    )
    assert case.case_number == "MP-2026-00001"
    assert case.name == "Test Person"
    assert case.status == "Missing" or case.status == "ACTIVE_INVESTIGATION"
    d = case.to_dict()
    assert d["name"] == "Test Person"


def test_public_submission_model():
    sub = PublicSubmission(
        submission_reference="MP-SUB-2026-123456",
        full_name="Reported Person",
        age=20,
        gender="Female",
        contact_email="reporter@example.com",
        contact_phone="+919876543210",
        complainant_name="Reporter Name"
    )
    assert sub.submission_reference == "MP-SUB-2026-123456"
    assert sub.status == "PENDING_VERIFICATION"
    d = sub.to_dict()
    assert d["full_name"] == "Reported Person"


def test_case_event_model():
    ev = CaseEvent(
        case_id=1,
        event_type="MATCH_CONFIRMED",
        previous_status="UNDER_MATCH_REVIEW",
        new_status="MATCH_CONFIRMED",
        actor_id="admin_1",
        actor_role="admin"
    )
    assert ev.case_id == 1
    assert ev.created_at is not None
    d = ev.to_dict()
    assert d["event_type"] == "MATCH_CONFIRMED"


def test_password_hashing():
    hashed = hash_password("SecurePassword123!")
    assert hashed != "SecurePassword123!"
    assert verify_password("SecurePassword123!", hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_validators():
    ok_e, _ = validate_email("valid.user@example.com")
    assert ok_e is True

    bad_e, _ = validate_email("invalid-email-format")
    assert bad_e is False

    ok_f, _ = validate_image_filename("photo.jpg")
    assert ok_f is True

    bad_f, _ = validate_image_filename("../photo.exe")
    assert bad_f is False
