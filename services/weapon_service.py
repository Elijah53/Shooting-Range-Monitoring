"""
services/weapon_service.py
---------------------------
Inventory CRUD for the `weapons` table.

NOTE: This is inventory management only — not linked to live detection.
Weapon events use a weapon_type string (e.g. "Pistol") from the detector,
never a weapon_id FK. See §7 scope rule.
"""

from __future__ import annotations

from typing import Optional

from database.database import execute, fetch_all, fetch_one
from models.weapon import Weapon


def get_all_weapons() -> list[Weapon]:
    rows = fetch_all("SELECT * FROM weapons ORDER BY weapon_id")
    return [Weapon.from_row(r) for r in rows]


def get_weapon_by_id(weapon_id: str) -> Optional[Weapon]:
    row = fetch_one("SELECT * FROM weapons WHERE weapon_id = %s", (weapon_id,))
    return Weapon.from_row(row) if row else None


def add_weapon(weapon_id: str, weapon_type: str, status: str = "Available") -> None:
    execute(
        "INSERT INTO weapons (weapon_id, weapon_type, status) VALUES (%s, %s, %s)",
        (weapon_id, weapon_type, status),
    )


def update_weapon(weapon_id: str, weapon_type: str, status: str) -> None:
    execute(
        "UPDATE weapons SET weapon_type = %s, status = %s WHERE weapon_id = %s",
        (weapon_type, status, weapon_id),
    )


def set_weapon_status(weapon_id: str, status: str) -> None:
    execute(
        "UPDATE weapons SET status = %s WHERE weapon_id = %s",
        (status, weapon_id),
    )


def delete_weapon(weapon_id: str) -> None:
    execute("DELETE FROM weapons WHERE weapon_id = %s", (weapon_id,))
