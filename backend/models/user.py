from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass(init=False)
class User:
    name: str
    email: str
    password_hash: str
    role: str  # 'admin', 'officer', 'public'
    is_active: bool
    created_at: datetime
    id: Optional[int]

    def __init__(self, name: str = "", email: str = "", password_hash: str = "", role: str = "",
                 is_active: bool = True, created_at: datetime = None, id: Optional[int] = None, username: str = None):
        self.name = name or username or ""
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.id = id

    # Property alias for backward compatibility with systems importing 'username'
    @property
    def username(self) -> str:
        return self.name

    @username.setter
    def username(self, val: str):
        self.name = val

    def to_dict(self):
        d = asdict(self)
        if self.id is None:
            d.pop("id")
        d["username"] = self.name
        return d


    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return None
        return cls(
            id=data.get("id"),
            name=data.get("name") or data.get("username"),
            email=data.get("email"),
            password_hash=data.get("password_hash"),
            role=data.get("role"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at")
        )


