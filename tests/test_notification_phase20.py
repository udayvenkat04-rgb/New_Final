"""
Unit & Integration Test Suite for Email Alert and Notification System (Phase 20).

Tests:
1. Valid SMTP configuration.
2. Missing SMTP configuration.
3. Invalid SMTP configuration.
4. Valid recipient email.
5. Invalid recipient email.
6. Missing recipient email.
7. Successful email delivery (Dev Mode).
8. SMTP failure handling.
9. Timeout handling.
10. Authentication failure.
11. Duplicate notification prevention (Idempotency).
12. Notification record creation.
13. Notification SENT status.
14. Notification FAILED status.
15. Retry behavior & MAX_NOTIFICATION_ATTEMPTS protection.
16. Email disabled development mode.
17. Admin authorization.
18. Officer authorization denial.
19. Confirmed match triggers notification.
20. Potential match does NOT trigger notification.
21. Reopening confirmed match does NOT duplicate email.
22. Email failure does NOT reverse match confirmation.
"""

import pytest
from datetime import datetime
from models.missing_person import MissingPerson
from models.match_review import MatchReview
from models.notification import Notification
from repositories.case_repository import CaseRepository
from repositories.match_review_repository import MatchReviewRepository
from repositories.notification_repository import NotificationRepository
from services.email_service import EmailService
from services.match_review import MatchReviewService
from services.notification_service import NotificationService


# ── Mock Repositories for Isolated Unit Testing ──────────────────────

class MockCaseRepository:
    def __init__(self):
        self.cases = {
            "MP-101": MissingPerson(id="MP-101", case_number="MP-2026-00101", name="Alice Smith", contact_name="John Smith", contact_email="alice_complainant@example.com", status="Missing"),
            "MP-102": MissingPerson(id="MP-102", case_number="MP-2026-00102", name="Bob Jones", contact_name="Dave Jones", contact_email=None, status="Missing"),
            "MP-103": MissingPerson(id="MP-103", case_number="MP-2026-00103", name="Charlie Brown", contact_name="Sally Brown", contact_email="invalid-email-address", status="Missing"),
            1: MissingPerson(id=1, case_number="MP-2026-00001", name="Alice Smith", contact_name="John Smith", contact_email="alice_complainant@example.com", status="Missing"),
        }

    def get_by_id(self, case_id):
        return self.cases.get(case_id) or self.cases.get(str(case_id))

    def update_status(self, case_id, status):
        c = self.get_by_id(case_id)
        if c:
            c.status = status
            return True
        return False

    def log_history(self, log):
        pass


class MockNotificationRepository:
    def __init__(self):
        self.notifications = {}
        self.next_id = 1

    def create_notification(self, notification: Notification) -> Notification:
        if notification.id is None:
            notification.id = self.next_id
            self.next_id += 1
        self.notifications[notification.id] = notification
        return notification

    def get_notification_by_id(self, notification_id: int) -> Notification:
        return self.notifications.get(notification_id)

    def get_notifications_by_case(self, case_id):
        return [n for n in self.notifications.values() if str(n.case_id) == str(case_id)]

    def get_notifications_by_match_review(self, match_review_id):
        return [n for n in self.notifications.values() if str(n.match_review_id) == str(match_review_id)]

    def get_pending_notifications(self):
        return [n for n in self.notifications.values() if n.status == "PENDING"]

    def mark_sent(self, notification_id: int, sent_at=None) -> bool:
        n = self.notifications.get(notification_id)
        if n:
            n.status = "SENT"
            n.sent_at = sent_at or datetime.utcnow()
            n.updated_at = datetime.utcnow()
            n.error_message = None
            return True
        return False

    def mark_failed(self, notification_id: int, error_message: str) -> bool:
        n = self.notifications.get(notification_id)
        if n:
            n.status = "FAILED"
            n.error_message = error_message
            n.updated_at = datetime.utcnow()
            return True
        return False

    def increment_attempt_count(self, notification_id: int, error_message=None) -> bool:
        n = self.notifications.get(notification_id)
        if n:
            n.attempt_count += 1
            n.updated_at = datetime.utcnow()
            if error_message:
                n.error_message = error_message
            return True
        return False

    def find_existing_confirmed_notification(self, match_review_id, case_id):
        for n in self.notifications.values():
            if str(n.match_review_id) == str(match_review_id) and n.status == "SENT":
                return n
        return None


class MockMatchReviewRepository:
    def __init__(self):
        self.reviews = {}
        self.audits = []
        self.next_id = 1

    def create_review(self, review: MatchReview) -> MatchReview:
        if review.id is None:
            review.id = self.next_id
            self.next_id += 1
        self.reviews[review.id] = review
        return review

    def get_review_by_id(self, review_id: int) -> MatchReview:
        return self.reviews.get(review_id)

    def update_review_decision(self, review_id: int, review_status: str, review_decision: str, reviewed_by: str, review_notes: str = None) -> bool:
        r = self.reviews.get(review_id)
        if r:
            r.review_status = review_status
            r.review_decision = review_decision
            r.reviewed_by = reviewed_by
            r.reviewed_at = datetime.utcnow()
            return True
        return False

    def create_audit_record(self, audit):
        self.audits.append(audit)
        return audit

    def get_review_history(self, review_id: int):
        return [a for a in self.audits if a.match_review_id == review_id]


# ── Test Cases ──────────────────────────────────────────────────────

@pytest.fixture
def notif_setup():
    case_repo = MockCaseRepository()
    notif_repo = MockNotificationRepository()
    email_svc = EmailService(email_enabled=False)
    notif_service = NotificationService(notification_repo=notif_repo, case_repo=case_repo, email_service=email_svc)
    
    review_repo = MockMatchReviewRepository()
    review_service = MatchReviewService(review_repo=review_repo, case_repo=case_repo, notification_service=notif_service)

    admin_user = {"username": "admin_alice", "role": "admin"}
    officer_user = {"username": "officer_bob", "role": "officer"}
    return notif_service, notif_repo, case_repo, review_service, review_repo, email_svc, admin_user, officer_user


def test_valid_smtp_configuration():
    """1. Valid SMTP configuration loading."""
    email_svc = EmailService(smtp_host="smtp.example.com", smtp_port=587, smtp_username="user@example.com", smtp_password="pwd")
    assert email_svc.smtp_host == "smtp.example.com"
    assert email_svc.smtp_port == 587


def test_missing_smtp_configuration():
    """2. Missing SMTP configuration returns status message."""
    email_svc = EmailService(smtp_host="", smtp_username="", smtp_password="", email_enabled=True)
    success, msg = email_svc.send_email("recipient@example.com", "Test", "Body")
    assert success is False
    assert msg == "SMTP_CONFIGURATION_MISSING"


def test_invalid_smtp_configuration():
    """3. Invalid SMTP server returns connection error."""
    email_svc = EmailService(smtp_host="invalid.nonexistent.domain.xyz", smtp_port=587, smtp_username="u", smtp_password="p", email_enabled=True)
    success, msg = email_svc.send_email("recipient@example.com", "Test", "Body")
    assert success is False
    assert "SMTP_CONNECTION_ERROR" in msg or "EMAIL_SEND_FAILED" in msg or "SMTP" in msg


def test_valid_recipient_email(notif_setup):
    """4. Valid recipient email formatting."""
    _, _, _, _, _, email_svc, _, _ = notif_setup
    assert email_svc.validate_email_address("valid.user@domain.com") is True
    assert email_svc.validate_email_address("user+test@sub.domain.org") is True


def test_invalid_recipient_email(notif_setup):
    """5. Invalid recipient email formatting rejection."""
    _, _, _, _, _, email_svc, _, _ = notif_setup
    assert email_svc.validate_email_address("invalid-email") is False
    assert email_svc.validate_email_address("@domain.com") is False
    assert email_svc.validate_email_address("") is False


def test_missing_recipient(notif_setup):
    """6. Missing recipient email records NO_VALID_RECIPIENT."""
    notif_service, notif_repo, _, _, _, _, admin_user, _ = notif_setup
    res = notif_service.process_match_confirmation_notification(match_review_id=10, case_id="MP-102", user=admin_user)

    assert res["status"] == "EMAIL_NOT_SENT"
    assert res["reason"] == "NO_VALID_RECIPIENT"
    assert res["notification"].status == "FAILED"
    assert res["notification"].error_message == "NO_VALID_RECIPIENT"


def test_successful_email_delivery_dev_mode(notif_setup):
    """7. Successful email delivery in EMAIL_ENABLED=false dev mode."""
    notif_service, notif_repo, _, _, _, _, admin_user, _ = notif_setup
    res = notif_service.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)

    assert res["status"] == "SENT"
    assert res["notification"].status == "SENT"
    assert res["notification"].recipient_email == "alice_complainant@example.com"


def test_smtp_failure_handling():
    """8. SMTP failure handling returns FAILED status without crashing."""
    class FailingEmailService(EmailService):
        def send_email(self, to_email, subject, body_text, body_html=None):
            return False, "SMTP_CONNECTION_TIMEOUT"

    case_repo = MockCaseRepository()
    notif_repo = MockNotificationRepository()
    svc = NotificationService(notification_repo=notif_repo, case_repo=case_repo, email_service=FailingEmailService())
    admin_user = {"username": "admin", "role": "admin"}

    res = svc.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    assert res["status"] == "FAILED"
    assert "SMTP_CONNECTION_TIMEOUT" in res["message"]
    assert res["notification"].status == "FAILED"


def test_smtp_timeout_handling():
    """9. Timeout exception handled gracefully."""
    class TimeoutEmailService(EmailService):
        def send_email(self, to_email, subject, body_text, body_html=None):
            return False, "SMTP_CONNECTION_ERROR: Connection timed out"

    svc = NotificationService(notification_repo=MockNotificationRepository(), case_repo=MockCaseRepository(), email_service=TimeoutEmailService())
    admin_user = {"username": "admin", "role": "admin"}
    res = svc.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    assert res["status"] == "FAILED"


def test_authentication_failure():
    """10. Authentication failure handled gracefully."""
    class AuthFailEmailService(EmailService):
        def send_email(self, to_email, subject, body_text, body_html=None):
            return False, "SMTP_AUTHENTICATION_FAILED"

    svc = NotificationService(notification_repo=MockNotificationRepository(), case_repo=MockCaseRepository(), email_service=AuthFailEmailService())
    admin_user = {"username": "admin", "role": "admin"}
    res = svc.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    assert res["status"] == "FAILED"


def test_duplicate_notification_prevention(notif_setup):
    """11. Idempotency check prevents duplicate emails."""
    notif_service, notif_repo, _, _, _, _, admin_user, _ = notif_setup
    res1 = notif_service.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    assert res1["status"] == "SENT"

    # Second call for same match review ID
    res2 = notif_service.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    assert res2["status"] == "ALREADY_SENT"
    assert len(notif_repo.notifications) == 1


def test_notification_record_creation(notif_setup):
    """12. Notification record created in MongoDB repository."""
    notif_service, notif_repo, _, _, _, _, admin_user, _ = notif_setup
    notif_service.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)

    assert len(notif_repo.notifications) == 1
    n = notif_repo.get_notification_by_id(1)
    assert n.case_id == "MP-101"
    assert n.match_review_id == 1
    assert n.recipient_email == "alice_complainant@example.com"


def test_notification_sent_status(notif_setup):
    """13. Mark sent updates status to SENT."""
    _, notif_repo, _, _, _, _, _, _ = notif_setup
    n = notif_repo.create_notification(Notification(case_id=1, match_review_id=1, recipient_email="a@b.com"))
    notif_repo.mark_sent(n.id)

    updated = notif_repo.get_notification_by_id(n.id)
    assert updated.status == "SENT"
    assert updated.sent_at is not None


def test_notification_failed_status(notif_setup):
    """14. Mark failed updates status to FAILED and records error message."""
    _, notif_repo, _, _, _, _, _, _ = notif_setup
    n = notif_repo.create_notification(Notification(case_id=1, match_review_id=1, recipient_email="a@b.com"))
    notif_repo.mark_failed(n.id, "SMTP connection error")

    updated = notif_repo.get_notification_by_id(n.id)
    assert updated.status == "FAILED"
    assert updated.error_message == "SMTP connection error"


def test_retry_behavior(notif_setup):
    """15. Retry behavior increments attempt count and enforces max attempts limit (3)."""
    class FailingEmailService(EmailService):
        def send_email(self, to_email, subject, body_text, body_html=None):
            return False, "SMTP_ERROR"

    case_repo = MockCaseRepository()
    notif_repo = MockNotificationRepository()
    svc = NotificationService(notification_repo=notif_repo, case_repo=case_repo, email_service=FailingEmailService())
    admin_user = {"username": "admin", "role": "admin"}

    res = svc.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    notif_id = res["notification"].id
    assert res["notification"].attempt_count == 1

    # Retry 1 (Attempt 2)
    svc.retry_failed_notification(notif_id, user=admin_user)
    n = notif_repo.get_notification_by_id(notif_id)
    assert n.attempt_count == 2

    # Retry 2 (Attempt 3)
    svc.retry_failed_notification(notif_id, user=admin_user)
    n = notif_repo.get_notification_by_id(notif_id)
    assert n.attempt_count == 3

    # Retry 3 (Attempt 4 -> Blocked by max_attempts=3)
    res_blocked = svc.retry_failed_notification(notif_id, user=admin_user)
    assert res_blocked["status"] == "FAILED"
    assert "Maximum retry attempts" in res_blocked["message"]


def test_email_disabled_dev_mode():
    """16. EMAIL_ENABLED=false development mode bypasses SMTP network connections."""
    email_svc = EmailService(email_enabled=False)
    success, msg = email_svc.send_email("test@example.com", "Subject", "Body")
    assert success is True
    assert msg == "EMAIL_DISABLED_DEVELOPMENT_MODE"


def test_admin_authorization(notif_setup):
    """17. Admin can trigger notification processing and retries."""
    notif_service, _, _, _, _, _, admin_user, _ = notif_setup
    res = notif_service.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=admin_user)
    assert res["status"] == "SENT"


def test_officer_authorization_denial(notif_setup):
    """18. Officer user raises PermissionError when attempting notification actions."""
    notif_service, _, _, _, _, _, _, officer_user = notif_setup
    with pytest.raises(PermissionError):
        notif_service.process_match_confirmation_notification(match_review_id=1, case_id="MP-101", user=officer_user)

    with pytest.raises(PermissionError):
        notif_service.retry_failed_notification(1, user=officer_user)


def test_confirmed_match_triggers_notification(notif_setup):
    """19. Confirming match in MatchReviewService triggers notification processing."""
    _, notif_repo, case_repo, review_service, review_repo, _, admin_user, _ = notif_setup
    r = review_service.create_potential_match(case_id="MP-101", similarity_score=95.0, distance=0.1)

    review_service.review_match(match_id=r.id, status="CONFIRMED", user=admin_user)

    # Check notification repository
    notifs = notif_repo.get_notifications_by_match_review(r.id)
    assert len(notifs) == 1
    assert notifs[0].status == "SENT"


def test_potential_match_does_not_trigger_notification(notif_setup):
    """20. Potential match (PENDING_REVIEW) does NOT trigger notification."""
    _, notif_repo, _, review_service, _, _, _, _ = notif_setup
    r = review_service.create_potential_match(case_id="MP-101", similarity_score=95.0, distance=0.1)

    notifs = notif_repo.get_notifications_by_match_review(r.id)
    assert len(notifs) == 0


def test_reopening_confirmed_match_does_not_duplicate_email(notif_setup):
    """21. Re-triggering confirmation returns ALREADY_SENT or is blocked."""
    notif_service, notif_repo, _, review_service, _, _, admin_user, _ = notif_setup
    r = review_service.create_potential_match(case_id="MP-101", similarity_score=95.0, distance=0.1)
    review_service.review_match(match_id=r.id, status="CONFIRMED", user=admin_user)

    # Direct notification service call for same match_review_id
    res_dup = notif_service.process_match_confirmation_notification(match_review_id=r.id, case_id="MP-101", user=admin_user)
    assert res_dup["status"] == "ALREADY_SENT"


def test_email_failure_does_not_reverse_match_confirmation():
    """22. Email failure does NOT reverse match confirmation ('CONFIRMED' and 'Found' remain)."""
    class FailingEmailService(EmailService):
        def send_email(self, to_email, subject, body_text, body_html=None):
            return False, "SMTP_SEND_FAILURE"

    case_repo = MockCaseRepository()
    notif_repo = MockNotificationRepository()
    review_repo = MockMatchReviewRepository()
    notif_svc = NotificationService(notification_repo=notif_repo, case_repo=case_repo, email_service=FailingEmailService())
    review_svc = MatchReviewService(review_repo=review_repo, case_repo=case_repo, notification_service=notif_svc)
    admin_user = {"username": "admin", "role": "admin"}

    r = review_svc.create_potential_match(case_id="MP-101", similarity_score=95.0, distance=0.1)
    success = review_svc.review_match(match_id=r.id, status="CONFIRMED", user=admin_user)

    assert success is True
    # Match review status MUST remain CONFIRMED
    updated_review = review_repo.get_review_by_id(r.id)
    assert updated_review.review_status == "CONFIRMED"

    # Case status MUST remain Found
    updated_case = case_repo.get_by_id("MP-101")
    assert updated_case.status == "Found"

    # Notification record MUST be FAILED
    notif = notif_repo.get_notifications_by_match_review(r.id)[0]
    assert notif.status == "FAILED"
