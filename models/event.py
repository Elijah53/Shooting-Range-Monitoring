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
    manual_weapon_type: Optional[str] = None
    manually_verified_by: Optional[str] = None
    manually_verified_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "WeaponEvent":
        return cls(
            event_id=row["event_id"],
            session_id=row.get("session_id"),
            user_id=row.get("user_id"),
            user_name=row.get("name") or row.get("user_name"),
            weapon_type=row["weapon_type"],
            confidence=float(row["confidence"]),
            detected_at=row["detected_at"],
            camera_id=row.get("camera_id"),
            lane_id=row.get("lane_id"),
            manual_weapon_type=row.get("manual_weapon_type"),
            manually_verified_by=row.get("manually_verified_by"),
            manually_verified_at=row.get("manually_verified_at"),
        )
