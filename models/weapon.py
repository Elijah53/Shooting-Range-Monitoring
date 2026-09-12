from dataclasses import dataclass


@dataclass
class Weapon:
    weapon_id: str
    weapon_type: str
    status: str  # 'Available' | 'In Use' | 'Maintenance'

    @classmethod
    def from_row(cls, row: dict) -> "Weapon":
        return cls(weapon_id=row["weapon_id"], weapon_type=row["weapon_type"], status=row["status"])
