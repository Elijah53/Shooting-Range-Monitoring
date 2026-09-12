from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    user_id: int
    name: str
    phone: Optional[str]
    registration_date: datetime
    status: str  # 'Active' | 'Inactive'
    has_face: bool = False  # convenience flag, not a DB column

    @classmethod
    def from_row(cls, row: dict) -> "User":
        return cls(
            user_id=row["user_id"],
            name=row["name"],
            phone=row.get("phone"),
            registration_date=row["registration_date"],
            status=row["status"],
            has_face=row.get("face_encoding") is not None,
        )
