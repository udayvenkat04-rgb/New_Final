"""
Case Event Data Model for Missing Person Identification System (Phase 23).

Defines the CaseEvent schema for recording immutable audit trail events
and deriving case timelines across the lifecycle state machine.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class CaseEvent:
    case_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    reason: Optional[str] = None
    source: str = "LIFECYCLE_SERVICE"
    related_entity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
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
    def from_dict(cls, data: Dict[str, Any]) -> Optional["CaseEvent"]:
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id"),
            event_type=data.get("event_type", "UNKNOWN"),
            previous_status=data.get("previous_status"),
            new_status=data.get("new_status"),
            actor_id=data.get("actor_id"),
            actor_role=data.get("actor_role"),
            reason=data.get("reason"),
            source=data.get("source", "LIFECYCLE_SERVICE"),
            related_entity_id=data.get("related_entity_id"),
            metadata=data.get("metadata"),
            created_at=data.get("created_at"),
        )
