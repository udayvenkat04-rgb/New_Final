"""
Notification Repository — Phase 20

Manages MongoDB persistence for the notifications collection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pymongo import DESCENDING

from backend.database import get_database
from backend.models.notification import Notification


class NotificationRepository:
    """Repository handling database operations for Notification entities."""

    def __init__(self):
        self.db = get_database()
        self.collection = self.db.notifications

    def create_notification(self, notification: Notification) -> Notification:
        """Creates a new Notification document with auto-incrementing integer ID."""
        if notification.id is None:
            max_doc = self.collection.find_one(sort=[("id", -1)])
            next_id = (max_doc.get("id") + 1) if (max_doc and isinstance(max_doc.get("id"), int)) else 1
            notification.id = next_id

        self.collection.insert_one(notification.to_dict())
        return notification

    def get_notification_by_id(self, notification_id: int) -> Optional[Notification]:
        """Retrieves a Notification by integer ID."""
        data = self.collection.find_one({"id": notification_id})
        return Notification.from_dict(data) if data else None

    def get_notifications_by_case(self, case_id: Union[str, int]) -> List[Notification]:
        """Returns all notifications associated with a case ID."""
        query = {"$or": [{"case_id": case_id}, {"case_id": str(case_id)}]}
        try:
            query["$or"].append({"case_id": int(case_id)})
        except Exception:
            pass

        docs = self.collection.find(query).sort("created_at", DESCENDING)
        return [Notification.from_dict(doc) for doc in docs if doc]

    def get_notifications_by_match_review(self, match_review_id: Union[str, int]) -> List[Notification]:
        """Returns all notifications associated with a match review ID."""
        query = {"$or": [{"match_review_id": match_review_id}, {"match_review_id": str(match_review_id)}]}
        try:
            query["$or"].append({"match_review_id": int(match_review_id)})
        except Exception:
            pass

        docs = self.collection.find(query).sort("created_at", DESCENDING)
        return [Notification.from_dict(doc) for doc in docs if doc]

    def get_pending_notifications(self) -> List[Notification]:
        """Returns all notifications currently in PENDING status."""
        docs = self.collection.find({"status": "PENDING"}).sort("created_at", DESCENDING)
        return [Notification.from_dict(doc) for doc in docs if doc]

    def mark_sent(self, notification_id: int, sent_at: Optional[datetime] = None) -> bool:
        """Marks a notification as SENT with timestamp."""
        now = sent_at or datetime.utcnow()
        res = self.collection.update_one(
            {"id": notification_id},
            {"$set": {"status": "SENT", "sent_at": now, "updated_at": now, "error_message": None}}
        )
        return res.modified_count > 0

    def mark_failed(self, notification_id: int, error_message: str) -> bool:
        """Marks a notification as FAILED with error message."""
        now = datetime.utcnow()
        res = self.collection.update_one(
            {"id": notification_id},
            {"$set": {"status": "FAILED", "error_message": error_message, "updated_at": now}}
        )
        return res.modified_count > 0

    def increment_attempt_count(self, notification_id: int, error_message: Optional[str] = None) -> bool:
        """Increments attempt count for a notification record."""
        now = datetime.utcnow()
        update_doc: Dict[str, Any] = {
            "$inc": {"attempt_count": 1},
            "$set": {"updated_at": now}
        }
        if error_message:
            update_doc["$set"]["error_message"] = error_message

        res = self.collection.update_one({"id": notification_id}, update_doc)
        return res.modified_count > 0

    def find_existing_confirmed_notification(
        self,
        match_review_id: Union[str, int],
        case_id: Union[str, int]
    ) -> Optional[Notification]:
        """
        Idempotency Check: Returns an existing notification with status SENT
        for the given match_review_id or case_id.
        """
        query = {
            "notification_type": "MATCH_CONFIRMED",
            "status": "SENT",
            "$or": [
                {"match_review_id": match_review_id},
                {"match_review_id": str(match_review_id)},
            ]
        }
        try:
            query["$or"].append({"match_review_id": int(match_review_id)})
        except Exception:
            pass

        data = self.collection.find_one(query)
        return Notification.from_dict(data) if data else None
