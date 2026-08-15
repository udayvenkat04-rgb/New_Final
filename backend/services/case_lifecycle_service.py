"""
Case Lifecycle Service for Missing Person Identification System (Phase 23).

Controls state machine transitions for official missing person cases across:
ACTIVE_INVESTIGATION -> POTENTIAL_MATCH -> UNDER_MATCH_REVIEW -> MATCH_CONFIRMED -> RESOLVED -> CLOSED -> REOPENED.

Enforces role-based transition matrices, concurrency optimistic locking,
immutable audit event creation (CaseEventRepository), and notification triggers.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

from backend.models.case_event import CaseEvent
from backend.repositories.case_repository import CaseRepository
from backend.repositories.case_event_repository import CaseEventRepository
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Standard Lifecycle State Constants
STATE_ACTIVE_INVESTIGATION = "ACTIVE_INVESTIGATION"
STATE_POTENTIAL_MATCH = "POTENTIAL_MATCH"
STATE_UNDER_MATCH_REVIEW = "UNDER_MATCH_REVIEW"
STATE_MATCH_CONFIRMED = "MATCH_CONFIRMED"
STATE_MATCH_REJECTED = "MATCH_REJECTED"
STATE_RESOLVED = "RESOLVED"
STATE_CLOSED = "CLOSED"
STATE_REOPENED = "REOPENED"

# Legacy Status Normalization Map
STATUS_ALIAS_MAP = {
    "MISSING": STATE_ACTIVE_INVESTIGATION,
    "ACTIVE": STATE_ACTIVE_INVESTIGATION,
    "ACTIVE_INVESTIGATION": STATE_ACTIVE_INVESTIGATION,
    "POTENTIAL_MATCH": STATE_POTENTIAL_MATCH,
    "UNDER_MATCH_REVIEW": STATE_UNDER_MATCH_REVIEW,
    "MATCH_CONFIRMED": STATE_MATCH_CONFIRMED,
    "MATCH_REJECTED": STATE_MATCH_REJECTED,
    "FOUND": STATE_RESOLVED,
    "RESOLVED": STATE_RESOLVED,
    "CLOSED": STATE_CLOSED,
    "REOPENED": STATE_REOPENED,
}

# Central Transition Matrix: (current_state, requested_state) -> metadata
TRANSITION_MATRIX = {
    (STATE_ACTIVE_INVESTIGATION, STATE_POTENTIAL_MATCH): {
        "allowed_roles": ["admin", "officer", "system"],
        "action": "POTENTIAL_MATCH_DETECTED",
        "description": "AI matching system identified candidate face match.",
        "trigger_notification": False,
    },
    (STATE_POTENTIAL_MATCH, STATE_UNDER_MATCH_REVIEW): {
        "allowed_roles": ["admin", "officer", "system"],
        "action": "MATCH_REVIEW_OPENED",
        "description": "Admin/Officer opened candidate match review.",
        "trigger_notification": False,
    },
    (STATE_ACTIVE_INVESTIGATION, STATE_UNDER_MATCH_REVIEW): {
        "allowed_roles": ["admin", "officer", "system"],
        "action": "MATCH_REVIEW_OPENED",
        "description": "Match candidate opened for active case review.",
        "trigger_notification": False,
    },
    (STATE_UNDER_MATCH_REVIEW, STATE_MATCH_CONFIRMED): {
        "allowed_roles": ["admin"],
        "action": "MATCH_CONFIRMED",
        "description": "Human review confirmed candidate face match.",
        "trigger_notification": True,
    },
    (STATE_UNDER_MATCH_REVIEW, STATE_MATCH_REJECTED): {
        "allowed_roles": ["admin"],
        "action": "MATCH_REJECTED",
        "description": "Human review rejected candidate face match.",
        "trigger_notification": False,
    },
    (STATE_MATCH_REJECTED, STATE_ACTIVE_INVESTIGATION): {
        "allowed_roles": ["admin", "officer", "system"],
        "action": "RESUMED_INVESTIGATION",
        "description": "Returned case to active investigation after match rejection.",
        "trigger_notification": False,
    },
    (STATE_MATCH_CONFIRMED, STATE_RESOLVED): {
        "allowed_roles": ["admin"],
        "action": "CASE_RESOLVED",
        "description": "Case resolved following match confirmation.",
        "trigger_notification": False,
        "requires_reason": True,
    },
    (STATE_ACTIVE_INVESTIGATION, STATE_RESOLVED): {
        "allowed_roles": ["admin"],
        "action": "CASE_RESOLVED",
        "description": "Case resolved by administrative action.",
        "trigger_notification": False,
        "requires_reason": True,
    },
    (STATE_RESOLVED, STATE_CLOSED): {
        "allowed_roles": ["admin"],
        "action": "CASE_CLOSED",
        "description": "Case closed by administrator.",
        "trigger_notification": False,
    },
    (STATE_CLOSED, STATE_REOPENED): {
        "allowed_roles": ["admin"],
        "action": "CASE_REOPENED",
        "description": "Case reopened for further investigation.",
        "trigger_notification": False,
        "requires_reason": True,
    },
    (STATE_REOPENED, STATE_ACTIVE_INVESTIGATION): {
        "allowed_roles": ["admin", "officer", "system"],
        "action": "ACTIVE_INVESTIGATION_RESUMED",
        "description": "Active investigation resumed following case reopening.",
        "trigger_notification": False,
    },
}


class CaseLifecycleService:
    def __init__(
        self,
        case_repo: Optional[CaseRepository] = None,
        event_repo: Optional[CaseEventRepository] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.case_repo = case_repo or CaseRepository()
        self.event_repo = event_repo or CaseEventRepository()
        self.notification_service = notification_service or NotificationService()

    def normalize_status(self, raw_status: Optional[str]) -> str:
        """Normalizes legacy or uppercase status string to standard lifecycle state."""
        if not raw_status:
            return STATE_ACTIVE_INVESTIGATION
        cleaned = str(raw_status).strip().upper()
        return STATUS_ALIAS_MAP.get(cleaned, cleaned)

    def is_transition_allowed(
        self,
        current_status: str,
        requested_status: str,
        user_role: str,
    ) -> Tuple[bool, str]:
        """Checks if a transition from current_status to requested_status is permitted for user_role."""
        curr_norm = self.normalize_status(current_status)
        req_norm = self.normalize_status(requested_status)

        if curr_norm == req_norm:
            return False, f"Case is already in '{curr_norm}' status."

        transition_rule = TRANSITION_MATRIX.get((curr_norm, req_norm))
        if not transition_rule:
            return False, f"Invalid transition: Cannot move from '{curr_norm}' to '{req_norm}'."

        role = str(user_role or "public").lower()
        if role not in transition_rule["allowed_roles"]:
            return False, f"Role '{role.upper()}' is not authorized to transition from '{curr_norm}' to '{req_norm}'."

        return True, "TRANSITION_ALLOWED"

    def transition_case_status(
        self,
        case_id: int,
        requested_status: str,
        user: Optional[Dict[str, Any]],
        reason: Optional[str] = None,
        expected_current_status: Optional[str] = None,
        related_match_review_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        Executes a controlled state transition for a case:
        1. Validates user authorization.
        2. Retrieves case & checks active non-deleted status.
        3. Enforces concurrency lock check if expected_current_status is specified.
        4. Validates transition matrix rules.
        5. Updates case status in CaseRepository.
        6. Logs immutable CaseEvent record in CaseEventRepository.
        7. Triggers NotificationService if rule requires email dispatch.
        """
        # User & Role Extraction
        if not user or not isinstance(user, dict):
            raise PermissionError("Authentication required for case lifecycle transitions.")
        actor_id = str(user.get("username") or user.get("id") or "unknown")
        actor_role = str(user.get("role") or "public").lower()

        # Fetch Case
        case = self.case_repo.get_by_id(case_id)
        if not case:
            return False, f"Case #{case_id} not found."
        if case.is_deleted:
            return False, f"Case #{case_id} has been soft-deleted."

        curr_norm = self.normalize_status(case.status)
        req_norm = self.normalize_status(requested_status)

        # Optimistic Concurrency Lock Check
        if expected_current_status:
            exp_norm = self.normalize_status(expected_current_status)
            if curr_norm != exp_norm:
                return False, f"STALE_TRANSITION: Case status has changed to '{curr_norm}'. Please refresh."

        # Validate Transition Rules
        allowed, msg = self.is_transition_allowed(curr_norm, req_norm, actor_role)
        if not allowed:
            if "not authorized" in msg:
                raise PermissionError(msg)
            return False, msg

        rule = TRANSITION_MATRIX.get((curr_norm, req_norm), {})
        if rule.get("requires_reason") and not (reason and reason.strip()):
            return False, f"A reason/notes is required to transition from '{curr_norm}' to '{req_norm}'."

        # Update Case Repository Status
        success = self.case_repo.update_status(case_id, req_norm)
        if not success:
            return False, "Failed to update case status in database."

        # Create Immutable Audit CaseEvent
        event = CaseEvent(
            case_id=case_id,
            event_type=rule.get("action", "STATUS_CHANGED"),
            previous_status=curr_norm,
            new_status=req_norm,
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason or rule.get("description"),
            source="CASE_LIFECYCLE_SERVICE",
            related_entity_id=related_match_review_id,
            metadata=metadata or {},
        )
        saved_event = self.event_repo.create_event(event)

        # Trigger Notification if required (e.g. MATCH_CONFIRMED)
        notification_info = ""
        if rule.get("trigger_notification"):
            try:
                # Build Notification Data
                match_data = {
                    "case_id": case_id,
                    "case_number": case.case_number,
                    "name": case.name,
                    "contact_email": case.contact_email,
                    "contact_name": case.contact_name,
                    "similarity": (metadata or {}).get("confidence", 95.0),
                    "review_id": related_match_review_id,
                    "review_notes": reason or "Match confirmed by administrator.",
                    "event_id": saved_event.id,
                }
                notif_sent, notif_msg = self.notification_service.send_match_confirmed_alert(match_data, user)
                if notif_sent:
                    notification_info = " (Notification alert sent successfully.)"
                else:
                    notification_info = f" (Notification alert failed: {notif_msg}. Transition remains intact.)"
            except Exception as e:
                logger.error("Error dispatching notification alert for case #%s: %s", case_id, e)
                notification_info = " (Notification attempt encountered an error. Transition remains intact.)"

        logger.info("Case #%s transitioned from '%s' to '%s' by %s (%s).", case_id, curr_norm, req_norm, actor_id, actor_role)
        return True, f"Case status updated from '{curr_norm}' to '{req_norm}' successfully.{notification_info}"

    def reopen_case(
        self,
        case_id: int,
        user: Optional[Dict[str, Any]],
        reason: str,
    ) -> Tuple[bool, str]:
        """Reopens a CLOSED case and sets status back to ACTIVE_INVESTIGATION."""
        case = self.case_repo.get_by_id(case_id)
        if not case:
            return False, f"Case #{case_id} not found."

        # Step 1: CLOSED -> REOPENED
        ok1, msg1 = self.transition_case_status(
            case_id=case_id,
            requested_status=STATE_REOPENED,
            user=user,
            reason=reason,
            expected_current_status=case.status,
        )
        if not ok1:
            return False, msg1

        # Step 2: REOPENED -> ACTIVE_INVESTIGATION
        ok2, msg2 = self.transition_case_status(
            case_id=case_id,
            requested_status=STATE_ACTIVE_INVESTIGATION,
            user=user,
            reason=f"Active investigation resumed after reopening: {reason}",
            expected_current_status=STATE_REOPENED,
        )
        return ok2, f"Case #{case_id} reopened successfully and set to ACTIVE_INVESTIGATION."

    def resolve_case(
        self,
        case_id: int,
        user: Optional[Dict[str, Any]],
        resolution_type: str,
        resolution_notes: str,
    ) -> Tuple[bool, str]:
        """Resolves a case (e.g. person found) with mandatory resolution notes and type."""
        reason_str = f"[{resolution_type.upper()}] {resolution_notes}".strip()
        metadata = {"resolution_type": resolution_type, "resolution_notes": resolution_notes}
        return self.transition_case_status(
            case_id=case_id,
            requested_status=STATE_RESOLVED,
            user=user,
            reason=reason_str,
            metadata=metadata,
        )

    def close_case(
        self,
        case_id: int,
        user: Optional[Dict[str, Any]],
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Closes a RESOLVED case bulletin."""
        return self.transition_case_status(
            case_id=case_id,
            requested_status=STATE_CLOSED,
            user=user,
            reason=notes or "Case closed by administrator.",
            expected_current_status=STATE_RESOLVED,
        )

    def get_case_timeline(self, case_id: int) -> List[Dict[str, Any]]:
        """
        Derives an ordered chronological timeline of events for a case
        combining CaseEvents and legacy CaseHistory.
        """
        timeline = []
        events = self.event_repo.get_case_events(case_id)
        for e in events:
            timeline.append({
                "id": f"event_{e.id}",
                "timestamp": e.created_at,
                "action": e.event_type,
                "actor": f"{e.actor_id or 'System'} ({e.actor_role or 'system'})",
                "previous_status": e.previous_status,
                "new_status": e.new_status,
                "description": e.reason or e.source,
                "type": "LIFECYCLE_EVENT",
            })

        history = self.case_repo.get_history_by_case(case_id)
        for h in history:
            # Avoid duplicating events if already covered
            t_dt = h.created_at or h.timestamp or datetime.utcnow()
            timeline.append({
                "id": f"hist_{h.id}",
                "timestamp": t_dt,
                "action": h.action,
                "actor": h.performed_by or "System",
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "description": h.details or h.notes,
                "type": "LEGACY_HISTORY",
            })

        # Sort combined timeline chronologically
        timeline.sort(key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min)
        return timeline
