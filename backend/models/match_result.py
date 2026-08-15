from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass(init=False)
class MatchResult:
    case_id: int
    sighting_id: int
    similarity: float
    status: str  # 'Pending Review', 'Confirmed Match', 'False Positive'
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    id: Optional[int]

    def __init__(self, case_id: int = 0, sighting_id: int = 0, similarity: float = 0.0, status: str = "Pending Review",
                 reviewed_by: Optional[str] = None, reviewed_at: Optional[datetime] = None, created_at: datetime = None,
                 id: Optional[int] = None, confidence: float = None, matched_at: datetime = None):
        self.case_id = case_id
        self.sighting_id = sighting_id
        self.similarity = similarity if confidence is None else confidence
        self.status = status
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
        self.created_at = created_at or matched_at or datetime.utcnow()
        self.id = id

    # Properties for legacy compatibility
    @property
    def confidence(self) -> float:
        return self.similarity
    @confidence.setter
    def confidence(self, value: float):
        self.similarity = value

    @property
    def review_status(self) -> str:
        return self.status
    @review_status.setter
    def review_status(self, value: str):
        self.status = value

    @property
    def source_type(self) -> str:
        return "IMAGE"

    @property
    def matched_at(self) -> datetime:
        return self.created_at
    @matched_at.setter
    def matched_at(self, value: datetime):
        self.created_at = value

    def to_dict(self):
        d = asdict(self)
        if self.id is None:
            d.pop("id")
        d["confidence"] = self.similarity
        d["matched_at"] = self.created_at
        return d


    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id"),
            sighting_id=data.get("sighting_id"),
            similarity=data.get("similarity") or data.get("confidence"),
            status=data.get("status", "Pending Review"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
            created_at=data.get("created_at") or data.get("matched_at")
        )


