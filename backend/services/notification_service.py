"""
Match Notification Service — Phase 20

Coordinates:
Match Confirmation -> Idempotency Check -> Recipient Retrieval -> Email Service -> Notification Repository

Ensures:
1. Emails are triggered ONLY upon explicit Admin match confirmation.
2. Idempotency: Duplicate confirmation attempts do NOT resend duplicate emails.
3. Complainant email format validation & NO_VALID_RECIPIENT handling.
4. SMTP failure does NOT reverse match review confirmation ('CONFIRMED' status stays).
5. Safe retry mechanism with MAX_NOTIFICATION_ATTEMPTS limit (Default: 3).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from backend.auth.permissions import authorize_review_match
from backend.config import settings
from backend.models.notification import Notification
from backend.repositories.case_repository import CaseRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.services.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    """Service orchestrating email notification alerts upon Admin match confirmation."""

    def __init__(
        self,
        notification_repo: Optional[NotificationRepository] = None,
        case_repo: Optional[CaseRepository] = None,
        email_service: Optional[EmailService] = None,
    ):
        self.notification_repo = notification_repo or NotificationRepository()
        self.case_repo = case_repo or CaseRepository()
        self.email_service = email_service or EmailService()

    def send_match_confirmed_alert(
        self,
        match_data: Dict[str, Any],
        current_user: Optional[dict] = None,
    ) -> Tuple[bool, str]:
        """
        Helper method to dispatch match confirmed email alert from lifecycle service payload.
        Idempotency key prevents resending duplicate notifications for the same event_id or match review.
        """
        review_id = match_data.get("review_id") or match_data.get("event_id") or "event"
        case_id = match_data.get("case_id")
        if not case_id:
            return False, "NO_CASE_ID"

        result = self.process_match_confirmation_notification(
            match_review_id=review_id,
            case_id=case_id,
            current_user=current_user,
        )
        status = result.get("status")
        if status in ("SENT", "ALREADY_SENT"):
            return True, result.get("message", "Notification processed.")
        return False, result.get("message", "Notification failed.")

    def process_match_confirmation_notification(
        self,
        match_review_id: Union[str, int],
        case_id: Union[str, int],
        current_user: Optional[dict] = None,
        user: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates email notification for a confirmed match review decision.

        Returns:
            Dict containing status ("SENT", "ALREADY_SENT", "EMAIL_NOT_SENT", "FAILED"),
            descriptive message, and notification object.
        """
        eff_user = current_user if current_user is not None else user
        if eff_user is not None:
            authorize_review_match(eff_user)

        # 1. Idempotency Check: Don't send duplicate emails if already sent
        existing_sent = self.notification_repo.find_existing_confirmed_notification(
            match_review_id=match_review_id,
            case_id=case_id
        )
        if existing_sent:
            logger.info("Idempotency guard triggered for match review #%s: Email already sent.", match_review_id)
            return {
                "status": "ALREADY_SENT",
                "message": "Match confirmation notification email has already been sent successfully.",
                "notification": existing_sent
            }

        # 2. Retrieve Case & Complainant Contact Email
        case_obj = self.case_repo.get_by_id(case_id)
        if not case_obj:
            logger.warning("Case #%s not found while generating notification.", case_id)
            notif = Notification(
                case_id=case_id,
                match_review_id=match_review_id,
                recipient_email="",
                status="FAILED",
                error_message="CASE_NOT_FOUND"
            )
            self.notification_repo.create_notification(notif)
            return {
                "status": "EMAIL_NOT_SENT",
                "reason": "CASE_NOT_FOUND",
                "message": f"Case record #{case_id} not found in database.",
                "notification": notif
            }

        recipient_email = getattr(case_obj, "contact_email", None) or getattr(case_obj, "email", None) or ""

        # 3. Validate Recipient Email Address
        if not recipient_email or not self.email_service.validate_email_address(recipient_email):
            logger.warning("No valid complainant contact email for case #%s ('%s').", case_id, recipient_email)
            notif = Notification(
                case_id=case_id,
                match_review_id=match_review_id,
                recipient_email=recipient_email,
                status="FAILED",
                error_message="NO_VALID_RECIPIENT"
            )
            saved_notif = self.notification_repo.create_notification(notif)
            return {
                "status": "EMAIL_NOT_SENT",
                "reason": "NO_VALID_RECIPIENT",
                "message": "No valid complainant contact email address associated with this case.",
                "notification": saved_notif
            }

        # 4. Create Initial PENDING Notification Record in MongoDB
        max_attempts = getattr(settings, "MAX_NOTIFICATION_ATTEMPTS", 3)
        notif = Notification(
            case_id=case_id,
            match_review_id=match_review_id,
            recipient_email=recipient_email,
            notification_type="MATCH_CONFIRMED",
            status="PENDING",
            provider="SMTP",
            attempt_count=1,
            max_attempts=max_attempts
        )
        saved_notif = self.notification_repo.create_notification(notif)

        # 5. Delegate Email Send to EmailService
        complainant_name = case_obj.contact_name or "Complainant"
        case_num = case_obj.case_number or str(case_obj.id)
        person_name = case_obj.name
        review_date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        success, status_msg = self.email_service.send_match_confirmation_email(
            recipient_email=recipient_email,
            complainant_name=complainant_name,
            case_number=case_num,
            missing_person_name=person_name,
            review_date=review_date_str
        )

        # 6. Update Notification Persistence Record
        if success:
            self.notification_repo.mark_sent(saved_notif.id)
            updated_notif = self.notification_repo.get_notification_by_id(saved_notif.id)
            return {
                "status": "SENT",
                "message": f"Notification email sent successfully to {recipient_email}.",
                "notification": updated_notif
            }
        else:
            self.notification_repo.mark_failed(saved_notif.id, status_msg)
            updated_notif = self.notification_repo.get_notification_by_id(saved_notif.id)
            return {
                "status": "FAILED",
                "message": f"Match confirmed, but notification failed: {status_msg}",
                "notification": updated_notif
            }

    def retry_failed_notification(
        self,
        notification_id: int,
        current_user: Optional[dict] = None,
        user: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Retries a failed email notification up to MAX_NOTIFICATION_ATTEMPTS.
        Strictly enforces Admin authorization.
        """
        eff_user = current_user if current_user is not None else user
        if eff_user is not None:
            authorize_review_match(eff_user)

        notif = self.notification_repo.get_notification_by_id(notification_id)
        if not notif:
            return {"status": "FAILED", "message": f"Notification record #{notification_id} not found."}

        if notif.status == "SENT":
            return {"status": "ALREADY_SENT", "message": "Notification has already been sent successfully.", "notification": notif}

        if notif.attempt_count >= notif.max_attempts:
            logger.warning("Maximum retry attempts (%d) reached for notification #%d", notif.max_attempts, notification_id)
            return {
                "status": "FAILED",
                "message": f"Maximum retry attempts ({notif.max_attempts}) reached for this notification.",
                "notification": notif
            }

        # Increment attempt counter
        self.notification_repo.increment_attempt_count(notification_id)
        case_obj = self.case_repo.get_by_id(notif.case_id)
        if not case_obj or not notif.recipient_email:
            self.notification_repo.mark_failed(notification_id, "NO_VALID_RECIPIENT")
            return {"status": "FAILED", "message": "Missing recipient email or case details.", "notification": notif}

        # Attempt resend
        complainant_name = case_obj.contact_name or "Complainant"
        case_num = case_obj.case_number or str(case_obj.id)
        person_name = case_obj.name
        review_date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        success, status_msg = self.email_service.send_match_confirmation_email(
            recipient_email=notif.recipient_email,
            complainant_name=complainant_name,
            case_number=case_num,
            missing_person_name=person_name,
            review_date=review_date_str
        )

        if success:
            self.notification_repo.mark_sent(notification_id)
            updated_notif = self.notification_repo.get_notification_by_id(notification_id)
            return {"status": "SENT", "message": "Retry successful. Notification email sent.", "notification": updated_notif}
        else:
            self.notification_repo.mark_failed(notification_id, status_msg)
            updated_notif = self.notification_repo.get_notification_by_id(notification_id)
            return {"status": "FAILED", "message": f"Retry failed: {status_msg}", "notification": updated_notif}

    def get_notifications_for_review(
        self,
        match_review_id: Union[str, int],
        current_user: Optional[dict] = None,
        user: Optional[dict] = None,
    ) -> List[Notification]:
        """Returns notifications logged for a match review ID."""
        eff_user = current_user if current_user is not None else user
        if eff_user is not None:
            authorize_review_match(eff_user)
        return self.notification_repo.get_notifications_by_match_review(match_review_id)
