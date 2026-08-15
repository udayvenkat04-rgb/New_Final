"""
Public Submission Data Models for Missing Person Identification System (Phase 22).

Contains PublicSubmission and PublicSubmissionAudit dataclasses.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class PublicSubmission:
    submission_reference: str
    full_name: str
    age: int
    gender: str
    complainant_name: str
    contact_email: str
    contact_phone: str
    height: Optional[str] = None
    identifying_features: Optional[str] = None
    description: Optional[str] = None
    last_seen_date: Optional[datetime] = None
    last_seen_time: Optional[str] = None
    last_seen_city: Optional[str] = None
    last_seen_state: Optional[str] = None
    last_seen_location: Optional[str] = None
    relationship: Optional[str] = None
    photo_path: Optional[str] = None
    status: str = "PENDING_VERIFICATION"
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    approved_case_id: Optional[int] = None
    is_possible_duplicate: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.id is None:
            d.pop("id", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["PublicSubmission"]:
        if not data:
            return None
        return cls(
            id=data.get("id") or data.get("_id"),
            submission_reference=data.get("submission_reference", ""),
            full_name=data.get("full_name", ""),
            age=data.get("age", 0),
            gender=data.get("gender", ""),
            height=data.get("height"),
            identifying_features=data.get("identifying_features"),
            description=data.get("description"),
            last_seen_date=data.get("last_seen_date"),
            last_seen_time=data.get("last_seen_time"),
            last_seen_city=data.get("last_seen_city"),
            last_seen_state=data.get("last_seen_state"),
            last_seen_location=data.get("last_seen_location"),
            complainant_name=data.get("complainant_name", ""),
            relationship=data.get("relationship"),
            contact_email=data.get("contact_email", ""),
            contact_phone=data.get("contact_phone", ""),
            photo_path=data.get("photo_path"),
            status=data.get("status", "PENDING_VERIFICATION"),
            review_notes=data.get("review_notes"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
            approved_case_id=data.get("approved_case_id"),
            is_possible_duplicate=data.get("is_possible_duplicate", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class PublicSubmissionAudit:
    submission_id: int
    submission_reference: str
    action: str
    actor_username: str
    actor_role: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None
    approved_case_id: Optional[int] = None
    created_at: Optional[datetime] = None
    id: Optional[int] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.id is None:
            d.pop("id", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["PublicSubmissionAudit"]:
        if not data:
            return None
        return cls(
            id=data.get("id") or data.get("_id"),
            submission_id=data.get("submission_id", 0),
            submission_reference=data.get("submission_reference", ""),
            action=data.get("action", ""),
            actor_username=data.get("actor_username", ""),
            actor_role=data.get("actor_role", ""),
            previous_status=data.get("previous_status"),
            new_status=data.get("new_status"),
            notes=data.get("notes"),
            approved_case_id=data.get("approved_case_id"),
            created_at=data.get("created_at"),
        )
