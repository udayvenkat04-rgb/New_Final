from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass(init=False)
class Sighting:
    case_id: Optional[int]
    created_at: datetime
    video_path: Optional[str]
    frame_number: Optional[int]
    timestamp_seconds: Optional[float]
    location: Optional[str]
    id: Optional[int]

    # Legacy fields preserved as optional/defaults for backwards compatibility
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    details: Optional[str]
    photo_path: Optional[str]
    reporter_name: str
    reporter_contact: str
    status: str
    sighting_time: datetime

    def __init__(self, case_id: Optional[int] = None, created_at: datetime = None, video_path: Optional[str] = None,
                 frame_number: Optional[int] = None, timestamp_seconds: Optional[float] = None, location: Optional[str] = None,
                 id: Optional[int] = None, address: Optional[str] = None, latitude: Optional[float] = None,
                 longitude: Optional[float] = None, details: Optional[str] = None, photo_path: Optional[str] = None,
                 reporter_name: str = "Anonymous", reporter_contact: str = "N/A", status: str = "Pending",
                 sighting_time: datetime = None):
         self.case_id = case_id
         self.created_at = created_at or datetime.utcnow()
         self.video_path = video_path
         self.frame_number = frame_number
         self.timestamp_seconds = timestamp_seconds
         self.location = location or address
         self.id = id
         
         self.address = address or location
         self.latitude = latitude
         self.longitude = longitude
         self.details = details
         self.photo_path = photo_path
         self.reporter_name = reporter_name
         self.reporter_contact = reporter_contact
         self.status = status
         self.sighting_time = sighting_time or datetime.utcnow()

    def to_dict(self):
        d = asdict(self)
        if self.id is None:
            d.pop("id")
        d["address"] = self.location or self.address
        return d


    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return None
        return cls(
            id=data.get("id"),
            case_id=data.get("case_id"),
            video_path=data.get("video_path"),
            frame_number=data.get("frame_number"),
            timestamp_seconds=data.get("timestamp_seconds"),
            location=data.get("location") or data.get("address"),
            created_at=data.get("created_at"),
            
            # Legacy compatibility fields
            address=data.get("address") or data.get("location"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            details=data.get("details"),
            photo_path=data.get("photo_path"),
            reporter_name=data.get("reporter_name", "Anonymous"),
            reporter_contact=data.get("reporter_contact", "N/A"),
            status=data.get("status", "Pending"),
            sighting_time=data.get("sighting_time")
        )


