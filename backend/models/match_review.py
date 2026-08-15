"""
Match Review & Audit Models — Phase 19

Defines structured dataclass models for human-in-the-loop match review decisions
and immutable audit history logs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


@dataclass
class MatchReview:
    """
    Represents a candidate face match queued or processed for human review.
    """
    id: Optional[int] = None
    case_id: Union[str, int] = ""
    sighting_id: Optional[Union[str, int]] = None
    source_type: str = "IMAGE"  # "IMAGE" or "VIDEO"
    source_reference: Optional[str] = None  # e.g., image path, video frame index
    similarity_score: float = 0.0
    distance: float = 0.0
    review_status: str = "PENDING_REVIEW"  # "PENDING_REVIEW", "CONFIRMED", "REJECTED", "NEEDS_FURTHER_REVIEW"
    review_decision: Optional[str] = None  # "CONFIRMED", "REJECTED", "NEEDS_FURTHER_REVIEW"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    first_seen_timestamp: Optional[float] = None
    last_seen_timestamp: Optional[float] = None
    detection_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def status(self) -> str:
        """Alias property for backwards compatibility with MatchResult."""
        return self.review_status

    @status.setter
    def status(self, value: str):
        self.review_status = value

    @property
    def confidence(self) -> float:
        return self.similarity_score

    @confidence.setter
    def confidence(self, value: float):
        self.similarity_score = value

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "case_id": self.case_id,
            "sighting_id": self.sighting_id,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "similarity_score": float(self.similarity_score),
            "distance": float(self.distance),
            "review_status": self.review_status,
            "review_decision": self.review_decision,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "review_notes": self.review_notes,
            "first_seen_timestamp": self.first_seen_timestamp,
            "last_seen_timestamp": self.last_seen_timestamp,
            "detection_count": self.detection_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # Backwards compatibility aliases
            "status": self.review_status,
            "confidence": float(self.similarity_score),
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Optional["MatchReview"]:
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id", ""),
            sighting_id=data.get("sighting_id"),
            source_type=data.get("source_type", "IMAGE"),
            source_reference=data.get("source_reference"),
            similarity_score=data.get("similarity_score") or data.get("confidence") or 0.0,
            distance=data.get("distance", 0.0),
            review_status=data.get("review_status") or data.get("status", "PENDING_REVIEW"),
            review_decision=data.get("review_decision"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
            review_notes=data.get("review_notes"),
            first_seen_timestamp=data.get("first_seen_timestamp"),
            last_seen_timestamp=data.get("last_seen_timestamp"),
            detection_count=data.get("detection_count"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class MatchReviewAudit:
    """
    Represents an immutable audit log entry for every human match review decision.
    """
    id: Optional[int] = None
    match_review_id: int = 0
    case_id: Union[str, int] = ""
    previous_status: str = "PENDING_REVIEW"
    new_status: str = "CONFIRMED"
    reviewer_id: str = "admin"
    reviewer_role: str = "admin"
    timestamp: Optional[datetime] = None
    review_notes: Optional[str] = None
    source_type: str = "IMAGE"

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "match_review_id": self.match_review_id,
            "case_id": self.case_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "timestamp": self.timestamp,
            "review_notes": self.review_notes,
            "source_type": self.source_type,
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Optional["MatchReviewAudit"]:
        if not data:
            return None
        return cls(
            id=data.get("id"),
            match_review_id=data.get("match_review_id", 0),
            case_id=data.get("case_id", ""),
            previous_status=data.get("previous_status", "PENDING_REVIEW"),
            new_status=data.get("new_status", ""),
            reviewer_id=data.get("reviewer_id", "admin"),
            reviewer_role=data.get("reviewer_role", "admin"),
            timestamp=data.get("timestamp"),
            review_notes=data.get("review_notes"),
            source_type=data.get("source_type", "IMAGE"),
        )
