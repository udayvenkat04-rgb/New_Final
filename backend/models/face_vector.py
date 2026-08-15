from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Union
import numpy as np


@dataclass(init=False)
class FaceVector:
    vector: List[float]
    case_id: Optional[int]
    dimensions: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    id: Optional[int]

    def __init__(
        self,
        vector: Union[List[float], np.ndarray] = None,
        case_id: Optional[int] = None,
        dimensions: Optional[int] = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        id: Optional[int] = None,
        embedding: Union[List[float], np.ndarray] = None,
        sighting_id: Optional[int] = None,
        photo_path: Optional[str] = None,
    ):
        raw_vec = vector if vector is not None else embedding
        if raw_vec is not None:
            if isinstance(raw_vec, np.ndarray):
                self.vector = [float(x) for x in raw_vec.tolist()]
            else:
                self.vector = [float(x) for x in raw_vec]
        else:
            self.vector = []

        self.case_id = int(case_id) if case_id is not None else None
        self.dimensions = int(dimensions) if dimensions is not None else len(self.vector)
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.id = int(id) if id is not None else None

    # Property alias for legacy compatibility
    @property
    def embedding(self) -> List[float]:
        return self.vector

    @embedding.setter
    def embedding(self, value: Union[List[float], np.ndarray]):
        if isinstance(value, np.ndarray):
            self.vector = [float(x) for x in value.tolist()]
        elif value is not None:
            self.vector = [float(x) for x in value]
        else:
            self.vector = []
        self.dimensions = len(self.vector) if self.vector else None

    def to_dict(self) -> dict:
        d = {
            "case_id": self.case_id,
            "vector": [float(x) for x in self.vector],
            "dimensions": self.dimensions or len(self.vector),
            "created_at": self.created_at,
            "updated_at": self.updated_at or self.created_at,
            "embedding": [float(x) for x in self.vector],
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Optional["FaceVector"]:
        if not data:
            return None
        vec = data.get("vector") or data.get("embedding") or []
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id"),
            vector=[float(x) for x in vec],
            dimensions=data.get("dimensions"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )



