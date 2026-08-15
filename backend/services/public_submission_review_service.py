"""
Public Submission Review Service for Missing Person Identification System (Phase 22).

Handles Admin authorization, submission queue retrieval, approval workflow (converting public reports
into official MissingPerson cases via CaseService), rejection workflow, and audit recording.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from backend.auth.permissions import authorize_review_match
from backend.models.missing_person import MissingPerson
from backend.models.public_submission import PublicSubmission, PublicSubmissionAudit
from backend.repositories.public_submission_repository import PublicSubmissionRepository
from backend.repositories.case_repository import CaseRepository
from backend.services.case_service import CaseService

logger = logging.getLogger(__name__)


class PublicSubmissionReviewService:
    def __init__(
        self,
        submission_repo: Optional[PublicSubmissionRepository] = None,
        case_repo: Optional[CaseRepository] = None,
        case_service: Optional[CaseService] = None,
    ):
        self.submission_repo = submission_repo or PublicSubmissionRepository()
        self.case_repo = case_repo or CaseRepository()
        self.case_service = case_service or CaseService(case_repo=self.case_repo)

    def _verify_admin_authorization(self, user: Optional[Dict[str, Any]]) -> str:
        """Enforces Admin role authorization. Raises PermissionError for Officers or public users."""
        if not user or not isinstance(user, dict):
            raise PermissionError("Authentication required for administrative review actions.")
        authorize_review_match(user)
        role = user.get("role", "").lower()
        if role != "admin":
            raise PermissionError("Only administrators can approve or reject public submissions.")
        return user.get("username", "admin")

    def get_pending_submissions(self, user: Optional[Dict[str, Any]]) -> List[PublicSubmission]:
        """Retrieves queue of pending public submissions for Admin review."""
        self._verify_admin_authorization(user)
        return self.submission_repo.get_pending_submissions()

    def get_all_submissions(
        self,
        user: Optional[Dict[str, Any]],
        status: Optional[str] = None,
    ) -> List[PublicSubmission]:
        """Retrieves all public submissions filtered by status."""
        self._verify_admin_authorization(user)
        return self.submission_repo.get_all_submissions(status=status)

    def get_submission_counts(self, user: Optional[Dict[str, Any]]) -> Dict[str, int]:
        """Returns statistics breakdown by submission status."""
        self._verify_admin_authorization(user)
        all_subs = self.submission_repo.get_all_submissions()
        counts = {
            "PENDING_VERIFICATION": 0,
            "APPROVED": 0,
            "REJECTED": 0,
            "DUPLICATE_POSSIBLE": 0,
            "TOTAL": len(all_subs),
        }
        for s in all_subs:
            st = s.status
            if st in counts:
                counts[st] += 1
            if s.is_possible_duplicate:
                counts["DUPLICATE_POSSIBLE"] += 1
        return counts

    def get_submission_details(
        self,
        submission_id: int,
        user: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[PublicSubmission], List[PublicSubmissionAudit]]:
        """Retrieves full submission details and audit history for Admin inspection."""
        self._verify_admin_authorization(user)
        sub = self.submission_repo.get_submission_by_id(submission_id)
        history = self.submission_repo.get_submission_history(submission_id) if sub else []
        return sub, history

    def approve_submission(
        self,
        submission_id: int,
        user: Optional[Dict[str, Any]],
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[int], str]:
        """
        Approves a public submission:
        1. Validates Admin authorization.
        2. Converts public submission into an official MissingPerson case via CaseService.
        3. Updates submission status to APPROVED, records approved_case_id, reviewer, and notes.
        4. Logs immutable PublicSubmissionAudit record.
        """
        actor_name = self._verify_admin_authorization(user)

        sub = self.submission_repo.get_submission_by_id(submission_id)
        if not sub:
            return False, None, f"Submission ID #{submission_id} not found."

        if sub.status == "APPROVED":
            return False, sub.approved_case_id, f"Submission #{sub.submission_reference} is already APPROVED."

        prev_status = sub.status

        # Build official MissingPerson case payload
        location_desc = sub.last_seen_location or f"{sub.last_seen_city or ''}, {sub.last_seen_state or ''}".strip(", ")
        desc = sub.description or ""
        if sub.identifying_features:
            desc = f"{desc}\nIdentifying Features: {sub.identifying_features}".strip()

        case_obj = MissingPerson(
            name=sub.full_name,
            age=sub.age,
            gender=sub.gender,
            last_seen_location=location_desc or "Not specified",
            last_seen_city=sub.last_seen_city,
            last_seen_state=sub.last_seen_state,
            last_seen_date=sub.last_seen_date or datetime.utcnow(),
            contact_name=sub.complainant_name,
            contact_email=sub.contact_email,
            contact_phone=sub.contact_phone,
            photo_path=sub.photo_path,
            description=desc,
            status="Missing",
            created_by=f"Approved Public Submission ({sub.submission_reference})",
        )
        if not case_obj.case_number and hasattr(self.case_repo, "get_next_case_number"):
            try:
                case_obj.case_number = self.case_repo.get_next_case_number(
                    year=(sub.last_seen_date.year if sub.last_seen_date else None)
                )
            except Exception:
                pass

        try:
            # Register official case in MongoDB via CaseRepository
            created_case = self.case_repo.create(case_obj)
            created_case_id = created_case.id if hasattr(created_case, "id") else None

            # Update Submission Record to APPROVED
            self.submission_repo.update_submission_status(
                submission_id=submission_id,
                status="APPROVED",
                reviewed_by=actor_name,
                review_notes=notes or "Approved by administrator.",
                approved_case_id=created_case_id,
            )

            # Log Immutable Audit Trail Record
            audit = PublicSubmissionAudit(
                submission_id=submission_id,
                submission_reference=sub.submission_reference,
                action="APPROVED",
                actor_username=actor_name,
                actor_role="admin",
                previous_status=prev_status,
                new_status="APPROVED",
                notes=notes or "Approved by admin and converted to official case.",
                approved_case_id=created_case_id,
            )
            self.submission_repo.create_audit_record(audit)

            logger.info("Public submission %s APPROVED by %s. Created Case ID #%s.", sub.submission_reference, actor_name, created_case_id)
            return True, created_case_id, f"Submission #{sub.submission_reference} approved and converted to Case #{created_case_id}."

        except Exception as e:
            logger.error("Failed to convert public submission %s to official case: %s", sub.submission_reference, e)
            return False, None, f"Failed to approve submission: {e}"

    def reject_submission(
        self,
        submission_id: int,
        user: Optional[Dict[str, Any]],
        reason: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Rejects a public submission:
        1. Validates Admin authorization.
        2. Updates submission status to REJECTED with administrative reason.
        3. Logs immutable PublicSubmissionAudit record.
        4. Does NOT delete submission record (remains auditable).
        """
        actor_name = self._verify_admin_authorization(user)

        sub = self.submission_repo.get_submission_by_id(submission_id)
        if not sub:
            return False, f"Submission ID #{submission_id} not found."

        if sub.status == "REJECTED":
            return False, f"Submission #{sub.submission_reference} is already REJECTED."

        prev_status = sub.status
        rejection_notes = reason or "Rejected by administrator."

        try:
            self.submission_repo.update_submission_status(
                submission_id=submission_id,
                status="REJECTED",
                reviewed_by=actor_name,
                review_notes=rejection_notes,
            )

            # Log Immutable Audit Trail Record
            audit = PublicSubmissionAudit(
                submission_id=submission_id,
                submission_reference=sub.submission_reference,
                action="REJECTED",
                actor_username=actor_name,
                actor_role="admin",
                previous_status=prev_status,
                new_status="REJECTED",
                notes=rejection_notes,
            )
            self.submission_repo.create_audit_record(audit)

            logger.info("Public submission %s REJECTED by %s. Reason: %s", sub.submission_reference, actor_name, rejection_notes)
            return True, f"Submission #{sub.submission_reference} rejected successfully."

        except Exception as e:
            logger.error("Failed to reject public submission %s: %s", sub.submission_reference, e)
            return False, f"Failed to reject submission: {e}"
