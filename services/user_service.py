"""
services/user_service.py
------------------------
CRUD operations for the `users` table.
All face-encoding serialisation/deserialisation is handled here.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from database.database import execute, fetch_all, fetch_one, fetch_scalar
from models.user import User
from vision.face_recognition import serialize_encoding, deserialize_encoding


# ── Read ───────────────────────────────────────────────────────────────────────

def get_all_users(include_inactive: bool = True) -> list[User]:
    if include_inactive:
        rows = fetch_all("SELECT * FROM users ORDER BY name")
    else:
        rows = fetch_all("SELECT * FROM users WHERE status='Active' ORDER BY name")
    return [User.from_row(r) for r in rows]


def get_user_by_id(user_id: int) -> Optional[User]:
    row = fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))
    return User.from_row(row) if row else None


def search_users(query: str) -> list[User]:
    like = f"%{query}%"
    rows = fetch_all(
        "SELECT * FROM users WHERE name ILIKE %s OR phone ILIKE %s ORDER BY name",
        (like, like),
    )
    return [User.from_row(r) for r in rows]


# ── Face encodings ────────────────────────────────────────────────────────────

def get_all_face_encodings() -> dict[int, tuple[str, np.ndarray]]:
    """
    Return {user_id: (name, encoding_array)} for all active users
    that have a registered face encoding.
    Used by the live recognition loop.
    """
    rows = fetch_all(
        "SELECT user_id, name, face_encoding FROM users "
        "WHERE face_encoding IS NOT NULL AND status = 'Active'"
    )
    result: dict[int, tuple[str, np.ndarray]] = {}
    for row in rows:
        if row["face_encoding"] is not None:
            try:
                enc = deserialize_encoding(bytes(row["face_encoding"]))
                result[row["user_id"]] = (row["name"], enc)
            except Exception:
                pass  # skip corrupted encodings silently
    return result


# ── Write ──────────────────────────────────────────────────────────────────────

def register_user(name: str, phone: str, encoding: Optional[np.ndarray] = None) -> int:
    """Insert a new user and return the new user_id."""
    enc_bytes = serialize_encoding(encoding) if encoding is not None else None
    row = fetch_one(
        """
        INSERT INTO users (name, phone, face_encoding)
        VALUES (%s, %s, %s)
        RETURNING user_id
        """,
        (name, phone, enc_bytes),
    )
    return row["user_id"]


def update_face_encoding(user_id: int, encoding: np.ndarray) -> None:
    enc_bytes = serialize_encoding(encoding)
    execute(
        "UPDATE users SET face_encoding = %s WHERE user_id = %s",
        (enc_bytes, user_id),
    )


def update_user(user_id: int, name: str, phone: str) -> None:
    execute(
        "UPDATE users SET name = %s, phone = %s WHERE user_id = %s",
        (name, phone, user_id),
    )


def deactivate_user(user_id: int) -> None:
    execute(
        "UPDATE users SET status = 'Inactive' WHERE user_id = %s",
        (user_id,),
    )


def activate_user(user_id: int) -> None:
    execute(
        "UPDATE users SET status = 'Active' WHERE user_id = %s",
        (user_id,),
    )
