from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WeaponEvent:
    event_id: int
    session_id: Optional[int]
    user_id: Optional[int]
    user_name: Optional[str]
    weapon_type: str
    confidence: float
    detected_at: datetime
    camera_id: Optional[str]
    lane_id: Optional[str]

    @classmethod
    def from_row(cls, row: dict) -> "WeaponEvent":
        return cls(
            event_id=row["event_id"],
            session_id=row.get("session_id"),
            user_id=row.get("user_id"),
            user_name=row.get("name"),
            weapon_type=row["weapon_type"],
            confidence=float(row["confidence"]),
            detected_at=row["detected_at"],
            camera_id=row.get("camera_id"),
            lane_id=row.get("lane_id"),
        )
