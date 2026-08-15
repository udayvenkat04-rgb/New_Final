from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass(init=False)
class CaseHistory:
    case_id: int
    action: str  # 'Case Created', 'Sighting Reported', 'Status Changed', etc.
    previous_status: Optional[str]
    new_status: Optional[str]
    performed_by: Optional[str]
    created_at: datetime
    details: Optional[str]
    id: Optional[int]

    def __init__(self, case_id: int = 0, action: str = "", previous_status: Optional[str] = None,
                 new_status: Optional[str] = None, performed_by: Optional[str] = None, created_at: datetime = None,
                 details: Optional[str] = None, id: Optional[int] = None, timestamp: datetime = None):
        self.case_id = case_id
        self.action = action
        self.previous_status = previous_status
        self.new_status = new_status
        self.performed_by = performed_by
        self.created_at = created_at or timestamp or datetime.utcnow()
        self.details = details
        self.id = id

    # Property alias for legacy compatibility
    @property
    def timestamp(self) -> datetime:
        return self.created_at
    @timestamp.setter
    def timestamp(self, value: datetime):
        self.created_at = value

    def to_dict(self):
        d = asdict(self)
        if self.id is None:
            d.pop("id")
        d["timestamp"] = self.created_at
        return d


    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id"),
            action=data.get("action"),
            previous_status=data.get("previous_status"),
            new_status=data.get("new_status"),
            performed_by=data.get("performed_by"),
            created_at=data.get("created_at") or data.get("timestamp"),
            details=data.get("details")
        )


