from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass(init=False)
class MissingPerson:
    name: str
    age: int
    gender: str
    last_seen_location: str
    last_seen_date: datetime
    case_number: Optional[str]
    description: Optional[str]
    last_seen_city: Optional[str]
    last_seen_state: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    photo_path: Optional[str]
    status: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime]
    id: Optional[int]

    def __init__(self, name: str = "", age: int = 0, gender: str = "", last_seen_location: str = "",
                 last_seen_date: datetime = None, case_number: Optional[str] = None, description: Optional[str] = None,
                 last_seen_city: Optional[str] = None, last_seen_state: Optional[str] = None,
                 latitude: Optional[float] = None, longitude: Optional[float] = None,
                 contact_name: Optional[str] = None, contact_email: Optional[str] = None, contact_phone: Optional[str] = None,
                 photo_path: Optional[str] = None, status: str = "Missing", created_by: Optional[str] = None,
                 created_at: datetime = None, updated_at: datetime = None, id: Optional[int] = None,
                 contact_number: Optional[str] = None, reporter_name: Optional[str] = None, reporter_contact: Optional[str] = None,
                 is_deleted: bool = False, deleted_at: Optional[datetime] = None):
        self.name = name
        self.age = age
        self.gender = gender
        self.last_seen_location = last_seen_location
        self.last_seen_date = last_seen_date or datetime.utcnow()
        self.case_number = case_number
        self.description = description
        self.last_seen_city = last_seen_city
        self.last_seen_state = last_seen_state
        self.latitude = latitude
        self.longitude = longitude
        self.contact_name = contact_name or reporter_name
        self.contact_email = contact_email
        self.contact_phone = contact_phone or contact_number or reporter_contact
        self.photo_path = photo_path
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.is_deleted = is_deleted
        self.deleted_at = deleted_at
        self.id = id

    # Properties for legacy compatibility
    @property
    def contact_number(self) -> Optional[str]:
        return self.contact_phone
    @contact_number.setter
    def contact_number(self, value: Optional[str]):
        self.contact_phone = value

    @property
    def reporter_name(self) -> Optional[str]:
        return self.contact_name
    @reporter_name.setter
    def reporter_name(self, value: Optional[str]):
        self.contact_name = value

    @property
    def reporter_contact(self) -> Optional[str]:
        return self.contact_phone
    @reporter_contact.setter
    def reporter_contact(self, value: Optional[str]):
        self.contact_phone = value

    def to_dict(self):
        d = asdict(self)
        if self.id is None:
            d.pop("id")
        # Sparse unique index on case_number only works when the field is ABSENT
        # for unnumbered cases, not when it's stored as null / None.
        if self.case_number is None:
            d.pop("case_number", None)
        d["contact_number"] = self.contact_phone
        d["reporter_name"] = self.contact_name
        d["reporter_contact"] = self.contact_phone
        return d


    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_number=data.get("case_number"),
            name=data.get("name"),
            age=data.get("age"),
            gender=data.get("gender"),
            description=data.get("description"),
            last_seen_location=data.get("last_seen_location"),
            last_seen_city=data.get("last_seen_city"),
            last_seen_state=data.get("last_seen_state"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            last_seen_date=data.get("last_seen_date"),
            contact_name=data.get("contact_name") or data.get("reporter_name"),
            contact_email=data.get("contact_email"),
            contact_phone=data.get("contact_phone") or data.get("contact_number") or data.get("reporter_contact"),
            photo_path=data.get("photo_path"),
            status=data.get("status", "Missing"),
            created_by=data.get("created_by"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_deleted=data.get("is_deleted", False),
            deleted_at=data.get("deleted_at"),
        )


