"""
services/session_service.py
----------------------------
Session lifecycle: start, reuse, end.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import streamlit as st
from database.database import execute, fetch_all, fetch_one, fetch_scalar


def get_active_session(user_id: int) -> Optional[dict]:
    """Return the currently-open session for a user, or None."""
    return fetch_one(
        """
        SELECT * FROM sessions
        WHERE user_id = %s AND status = 'Active'
        ORDER BY start_time DESC
        LIMIT 1
        """,
        (user_id,),
    )


def start_session(user_id: int, lane_id: str) -> int:
    """
    Start a new session for *user_id* in *lane_id*.
    If an active session already exists, return its id (no duplicate).
    Returns the session_id.
    """
    existing = get_active_session(user_id)
    if existing:
        return existing["session_id"]

    row = fetch_one(
        """
        INSERT INTO sessions (user_id, lane_id, status)
        VALUES (%s, %s, 'Active')
        RETURNING session_id
        """,
        (user_id, lane_id),
    )
    return row["session_id"]


def end_session(session_id: int) -> bool:
    """
    Mark a session as Completed and set end_time.
    Returns True on success, False if the session was not found or already closed.
    """
    row = fetch_one(
        "SELECT status FROM sessions WHERE session_id = %s",
        (session_id,),
    )
    if row is None or row["status"] != "Active":
        return False

    execute(
        """
        UPDATE sessions
        SET end_time = NOW(), status = 'Completed'
        WHERE session_id = %s
        """,
        (session_id,),
    )
    return True


def get_active_sessions() -> list[dict]:
    return fetch_all(
        """
        SELECT s.*, u.name AS user_name, u.name AS name
        FROM sessions s
        JOIN users u ON u.user_id = s.user_id
        WHERE s.status = 'Active'
        ORDER BY s.start_time DESC
        """
    )


@st.cache_data(ttl=30)
def count_active_sessions() -> int:
    """Count active sessions. Cached 30 s."""
    return fetch_scalar("SELECT COUNT(*) FROM sessions WHERE status = 'Active'") or 0


def get_all_sessions(
    user_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    from_date = from_date or date_from
    to_date = to_date or date_to
    clauses: list[str] = []
    params: list = []

    if user_id is not None:
        clauses.append("s.user_id = %s")
        params.append(user_id)
    from_date = from_date or date_from
    to_date = to_date or date_to
    if from_date is not None:
        clauses.append("s.start_time::date >= %s")
        params.append(from_date)
    if to_date is not None:
        clauses.append("s.start_time::date <= %s")
        params.append(to_date)
    if status:
        clauses.append("s.status = %s")
        params.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT s.*, u.name AS user_name, u.name AS name
        FROM sessions s
        JOIN users u ON u.user_id = s.user_id
        {where}
        ORDER BY s.start_time DESC
    """
    return fetch_all(sql, tuple(params) if params else None)
