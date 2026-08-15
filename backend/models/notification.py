"""
Notification Model — Phase 20

Defines structured dataclass model for email alert & notification tracking.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union


@dataclass
class Notification:
    """
    Represents an email alert notification record tied to a case and match review decision.
    """
    id: Optional[int] = None
    case_id: Union[str, int] = ""
    match_review_id: Union[str, int] = ""
    recipient_email: str = ""
    notification_type: str = "MATCH_CONFIRMED"
    status: str = "PENDING"  # "PENDING", "SENT", "FAILED", "EMAIL_NOT_SENT", "ALREADY_SENT"
    provider: str = "SMTP"
    attempt_count: int = 0
    max_attempts: int = 3
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "case_id": self.case_id,
            "match_review_id": self.match_review_id,
            "recipient_email": self.recipient_email,
            "notification_type": self.notification_type,
            "status": self.status,
            "provider": self.provider,
            "attempt_count": int(self.attempt_count),
            "max_attempts": int(self.max_attempts),
            "error_message": self.error_message,
            "sent_at": self.sent_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Optional["Notification"]:
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id", ""),
            match_review_id=data.get("match_review_id", ""),
            recipient_email=data.get("recipient_email", ""),
            notification_type=data.get("notification_type", "MATCH_CONFIRMED"),
            status=data.get("status", "PENDING"),
            provider=data.get("provider", "SMTP"),
            attempt_count=data.get("attempt_count", 0),
            max_attempts=data.get("max_attempts", 3),
            error_message=data.get("error_message"),
            sent_at=data.get("sent_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
