from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    session_id: int
    user_id: int
    user_name: Optional[str]
    lane_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # 'Active' | 'Completed'

    @classmethod
    def from_row(cls, row: dict) -> "Session":
        return cls(
            session_id=row["session_id"],
            user_id=row["user_id"],
            user_name=row.get("name"),
            lane_id=row["lane_id"],
            start_time=row["start_time"],
            end_time=row.get("end_time"),
            status=row["status"],
        )
